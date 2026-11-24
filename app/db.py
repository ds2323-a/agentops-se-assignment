"""数据访问层：SQLite 连接池、可回滚迁移、种子数据。

所有 schema 变更通过 migrations 表管理，重复启动幂等。
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import Settings
from .logging_util import info

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'engineer',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    project     TEXT NOT NULL DEFAULT 'Demo',
    status      TEXT NOT NULL DEFAULT 'todo',   -- todo/running/done/blocked
    level       TEXT NOT NULL DEFAULT 'L2',     -- L1/L2/L3 分级
    owner       TEXT NOT NULL DEFAULT 'unassigned',
    priority    INTEGER NOT NULL DEFAULT 3,     -- 1 最高
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS plan_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_no     INTEGER NOT NULL,
    title       TEXT NOT NULL,
    level       TEXT NOT NULL,                  -- L1/L2/L3
    agent       TEXT NOT NULL,                  -- 负责的 agent 或 human
    est_minutes INTEGER NOT NULL DEFAULT 10,
    status      TEXT NOT NULL DEFAULT 'pending',
    UNIQUE(task_id, step_no)
);

CREATE TABLE IF NOT EXISTS defects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    category    TEXT NOT NULL,                  -- 缺陷类别（帕累托分析维度）
    severity    TEXT NOT NULL,                  -- critical/major/minor
    cause_type  TEXT NOT NULL,                  -- agent/human/tool/requirement
    phase       TEXT NOT NULL,                  -- 引入阶段
    description TEXT NOT NULL DEFAULT '',
    detected_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_id     INTEGER REFERENCES plan_steps(id) ON DELETE SET NULL,
    agent_name  TEXT NOT NULL,
    outcome     TEXT NOT NULL,                  -- success/failure/escalated
    latency_ms  INTEGER NOT NULL DEFAULT 0,
    retries     INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS failure_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_name  TEXT NOT NULL,
    score       REAL NOT NULL,                  -- 0-100，越低越不可靠
    reliability TEXT NOT NULL,                  -- A/B/C/D
    computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_SEED_TASKS = [
    ("搭建用户认证模块", "实现登录、JWT 刷新与 RBAC 权限校验", "AgentOps", "done", "L1", "alice", 1),
    ("生成需求规格说明书", "根据访谈纪要生成 SRS 并输出用例图", "AgentOps", "done", "L2", "bob", 2),
    ("设计订单中心数据库", "完成 ER 建模、索引设计与迁移脚本", "AgentOps", "running", "L2", "alice", 2),
    ("编写支付回调接口", "对接第三方支付，含幂等与签名校验", "AgentOps", "blocked", "L3", "carol", 1),
    ("前端仪表盘开发", "实现任务看板、图表与失效分析视图", "AgentOps", "running", "L2", "bob", 2),
    ("批量数据清洗脚本", "清洗历史 CSV 并生成统计报表", "DataHub", "done", "L1", "agent-auto", 3),
    ("日志检索服务", "基于关键字与时间的日志查询 API", "DataHub", "done", "L1", "agent-auto", 3),
    ("风控规则引擎", "规则编排与命中解释，需人工确认策略", "DataHub", "blocked", "L3", "carol", 1),
    ("导出 Excel 周报", "按模板生成周报并发送邮件", "DataHub", "done", "L1", "agent-auto", 4),
    ("移动端适配改造", "响应式布局与交互走查", "AgentOps", "todo", "L2", "bob", 3),
]

_SEED_DEFECTS = [
    # (task_id, category, severity, cause_type, phase) —— 类别收敛后帕累托分析才有意义
    (1, "需求理解偏差", "major", "agent", "需求分析"),
    (1, "代码生成错误", "minor", "agent", "编码实现"),
    (2, "需求理解偏差", "major", "human", "需求评审"),
    (2, "文档结构缺失", "minor", "agent", "文档生成"),
    (3, "数据模型缺陷", "major", "agent", "数据库设计"),
    (3, "数据模型缺陷", "critical", "agent", "数据库设计"),
    (3, "需求理解偏差", "minor", "human", "需求评审"),
    (4, "代码生成错误", "critical", "tool", "编码实现"),
    (4, "代码生成错误", "major", "agent", "编码实现"),
    (4, "需求理解偏差", "major", "human", "详细设计"),
    (4, "工具链异常", "minor", "tool", "集成测试"),
    (5, "代码生成错误", "minor", "agent", "前端开发"),
    (5, "接口契约不一致", "major", "agent", "前端开发"),
    (5, "测试用例缺失", "minor", "human", "集成测试"),
    (6, "代码生成错误", "minor", "agent", "数据清洗"),
    (7, "接口契约不一致", "major", "agent", "编码实现"),
    (8, "需求理解偏差", "critical", "human", "策略设计"),
    (8, "文档结构缺失", "minor", "agent", "策略设计"),
]

_PLAN_TEMPLATES = {
    "L1": [
        (1, "任务解析与目标澄清", "L1", "Planner-Agent", 5),
        (2, "代码/内容自动生成", "L1", "Coder-Agent", 25),
        (3, "自动化校验与交付", "L1", "QA-Agent", 10),
    ],
    "L2": [
        (1, "需求拆解与计划生成", "L2", "Planner-Agent", 15),
        (2, "候选方案生成（AI）", "L1", "Coder-Agent", 25),
        (3, "人工评审与修正", "L2", "human", 30),
        (4, "回归验证与合并", "L2", "QA-Agent", 15),
    ],
    "L3": [
        (1, "目标澄清与风险识别", "L3", "human", 20),
        (2, "资料检索与草案辅助", "L1", "Retriever-Agent", 20),
        (3, "人工决策与最终签署", "L3", "human", 45),
        (4, "失效复盘记录", "L2", "Reviewer-Agent", 15),
    ],
}


def _hash_password(password: str) -> str:
    return hashlib.sha256(("agentops::" + password).encode("utf-8")).hexdigest()


class Database:
    """轻量连接池：每线程一个连接，避免跨线程共享 sqlite3 连接。"""

    def __init__(self, settings: Settings):
        self.path = str(Path(settings.db_path).resolve())
        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._migrate()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 30000")
            self._local.conn = conn
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._conn()
        with self._write_lock:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except Exception:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    def _migrate(self) -> None:
        with self._write_lock:
            conn = self._conn()
            conn.executescript(_SCHEMA)
            conn.execute("CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
            applied = {r[0] for r in conn.execute("SELECT name FROM migrations")}
            if "0001_initial" not in applied:
                conn.execute("INSERT INTO migrations(name) VALUES('0001_initial')")
            info("db_migrated", db_path=self.path, migrations=sorted(applied | {"0001_initial"}))
        self._seed_if_empty()

    def _seed_if_empty(self) -> None:
        conn = self._conn()
        if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] > 0:
            return
        with self.transaction() as tx:
            tx.executemany(
                "INSERT INTO users(username,password_hash,display_name,role) VALUES(?,?,?,?)",
                [
                    ("admin", _hash_password("admin123"), "系统管理员", "admin"),
                    ("alice", _hash_password("alice123"), " Alice · 前端", "engineer"),
                    ("bob", _hash_password("bob123"), "Bob · 测试", "engineer"),
                ],
            )
            tx.executemany(
                "INSERT INTO tasks(title,description,project,status,level,owner,priority) VALUES(?,?,?,?,?,?,?)",
                _SEED_TASKS,
            )
            rows = tx.execute("SELECT id, level, status FROM tasks ORDER BY id").fetchall()
            for row in rows:
                for step_no, title, level, agent, minutes in _PLAN_TEMPLATES[row["level"]]:
                    tx.execute(
                        "INSERT INTO plan_steps(task_id,step_no,title,level,agent,est_minutes,status) VALUES(?,?,?,?,?,?,?)",
                        (row["id"], step_no, title, level, agent, minutes,
                         "done" if row["status"] == "done" else ("running" if step_no == 2 and row["status"] == "running" else "pending")),
                    )
            tx.executemany(
                "INSERT INTO defects(task_id,category,severity,cause_type,phase,description) VALUES(?,?,?,?,?,?)",
                [(t, c, s, ct, ph, f"{ph}阶段发现：{c}") for t, c, s, ct, ph in _SEED_DEFECTS],
            )
            # 失效评分：按任务分级与缺陷严重度给出可解释分数
            severity_weight = {"critical": 18, "major": 9, "minor": 3}
            for row in rows:
                ds = tx.execute("SELECT severity FROM defects WHERE task_id=?", (row["id"],)).fetchall()
                penalty = sum(severity_weight[d["severity"]] for d in ds)
                base = {"L1": 98, "L2": 94, "L3": 88}[row["level"]]
                score = max(20.0, round(base - penalty * 0.55, 1))
                grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D"
                tx.execute(
                    "INSERT INTO failure_scores(task_id,agent_name,score,reliability) VALUES(?,?,?,?)",
                    (row["id"], "Planner-Agent" if row["level"] != "L3" else "Reviewer-Agent", score, grade),
                )
            info("db_seeded", tasks=len(_SEED_TASKS), defects=len(_SEED_DEFECTS))

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return list(self._conn().execute(sql, params).fetchall())

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._conn().execute(sql, params).fetchone()

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
