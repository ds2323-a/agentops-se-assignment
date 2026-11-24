"""服务层：承载业务规则（AI Agent 分级规划、失效评分），不依赖 HTTP 类型。"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .db import Database
from .errors import ConflictError, NotFoundError, ValidationError

# ---------------------------------------------------------------- 分级规则
# L1：Agent 自动完成；L2：人机协助；L3：纯人工
L1_KEYWORDS = ("生成", "导出", "清洗", "格式化", "模板", "批量", "转换", "统计", "检索", "周报")
L2_KEYWORDS = ("设计", "开发", "接口", "前端", "测试", "重构", "集成", "看板", "文档")
L3_KEYWORDS = ("风控", "支付", "签名", "策略", "决策", "签署", "安全", "合规", "审批")

LEVEL_LABEL = {
    "L1": "Agent 自动完成",
    "L2": "人机协助完成",
    "L3": "纯人工完成",
}

PLAN_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "L1": [
        {"step_no": 1, "title": "任务解析与目标澄清", "level": "L1", "agent": "Planner-Agent", "est_minutes": 5},
        {"step_no": 2, "title": "自动生成与自检", "level": "L1", "agent": "Coder-Agent", "est_minutes": 25},
        {"step_no": 3, "title": "自动化校验与交付", "level": "L1", "agent": "QA-Agent", "est_minutes": 10},
    ],
    "L2": [
        {"step_no": 1, "title": "需求拆解与计划生成", "level": "L2", "agent": "Planner-Agent", "est_minutes": 15},
        {"step_no": 2, "title": "候选方案生成（AI）", "level": "L1", "agent": "Coder-Agent", "est_minutes": 25},
        {"step_no": 3, "title": "人工评审与修正", "level": "L2", "agent": "human", "est_minutes": 30},
        {"step_no": 4, "title": "回归验证与合并", "level": "L2", "agent": "QA-Agent", "est_minutes": 15},
    ],
    "L3": [
        {"step_no": 1, "title": "目标澄清与风险识别", "level": "L3", "agent": "human", "est_minutes": 20},
        {"step_no": 2, "title": "资料检索与草案辅助", "level": "L1", "agent": "Retriever-Agent", "est_minutes": 20},
        {"step_no": 3, "title": "人工决策与最终签署", "level": "L3", "agent": "human", "est_minutes": 45},
        {"step_no": 4, "title": "失效复盘记录", "level": "L2", "agent": "Reviewer-Agent", "est_minutes": 15},
    ],
}


def classify_text(title: str, description: str = "") -> dict[str, Any]:
    """规则化分级规划器：根据任务文本计算风险分并映射到 L1/L2/L3。

    该函数是「AI 分级规划」的可解释内核：命中关键词 + 风险加权 → 分级 + 依据。
    """
    text = f"{title} {description}"
    hits_l1 = [k for k in L1_KEYWORDS if k in text]
    hits_l2 = [k for k in L2_KEYWORDS if k in text]
    hits_l3 = [k for k in L3_KEYWORDS if k in text]

    score = 14 + 6 * len(hits_l2) + 20 * len(hits_l3) - 4 * len(hits_l1)
    if re.search(r"[0-9]{4,}", text):
        score += 3
    score = max(5, min(98, score))

    if score >= 55:
        level = "L3"
    elif score >= 25:
        level = "L2"
    else:
        level = "L1"

    reasons = []
    if hits_l3:
        reasons.append(f"高风险关键词：{'、'.join(hits_l3)}")
    if hits_l2:
        reasons.append(f"需人工协同环节：{'、'.join(hits_l2)}")
    if hits_l1:
        reasons.append(f"可自动化环节：{'、'.join(hits_l1)}")
    if not reasons:
        reasons.append("任务边界清晰、风险较低，默认由 Agent 自动完成")

    return {
        "level": level,
        "label": LEVEL_LABEL[level],
        "risk_score": score,
        "reasons": reasons,
        "auto_assignable": level == "L1",
    }


class TaskService:
    def __init__(self, db: Database):
        self.db = db

    def list(self, status: str | None = None, level: str | None = None,
             project: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where, params = [], []
        if status:
            where.append("status = ?"); params.append(status)
        if level:
            where.append("level = ?"); params.append(level)
        if project:
            where.append("project = ?"); params.append(project)
        sql = "SELECT * FROM tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY priority ASC, id ASC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        return [dict(r) for r in self.db.query(sql, tuple(params))]

    def get(self, task_id: int) -> dict[str, Any]:
        row = self.db.one("SELECT * FROM tasks WHERE id=?", (task_id,))
        if row is None:
            raise NotFoundError(f"任务 {task_id} 不存在")
        return dict(row)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = (payload.get("title") or "").strip()
        if len(title) < 2 or len(title) > 120:
            raise ValidationError("title 长度需在 2-120 之间")
        description = str(payload.get("description") or "").strip()[:2000]
        project = str(payload.get("project") or "Demo").strip()[:60]
        owner = str(payload.get("owner") or "unassigned").strip()[:40]
        priority = payload.get("priority", 3)
        if not isinstance(priority, int) or not 1 <= priority <= 5:
            raise ValidationError("priority 需为 1-5 的整数")
        status = str(payload.get("status") or "todo")
        if status not in {"todo", "running", "done", "blocked"}:
            raise ValidationError("status 取值非法")

        # 分级：显式指定或由规则引擎推断
        if payload.get("level"):
            level = str(payload["level"]).upper()
            if level not in LEVEL_LABEL:
                raise ValidationError("level 只能是 L1/L2/L3")
            planning = {"level": level, "label": LEVEL_LABEL[level],
                        "risk_score": {"L1": 10, "L2": 40, "L3": 75}[level],
                        "reasons": ["由用户显式指定分级"], "auto_assignable": level == "L1"}
        else:
            planning = classify_text(title, description)
            level = planning["level"]

        with self.db.transaction() as tx:
            cur = tx.execute(
                "INSERT INTO tasks(title,description,project,status,level,owner,priority) VALUES(?,?,?,?,?,?,?)",
                (title, description, project, status, level, owner, priority),
            )
            task_id = cur.lastrowid
            for step in PLAN_TEMPLATES[level]:
                tx.execute(
                    "INSERT INTO plan_steps(task_id,step_no,title,level,agent,est_minutes,status) VALUES(?,?,?,?,?,?,?)",
                    (task_id, step["step_no"], step["title"], step["level"],
                     step["agent"], step["est_minutes"], "pending"),
                )
        return {**self.get(task_id), "planning": planning}

    def update(self, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.get(task_id)
        allowed = {"title", "description", "project", "status", "level", "owner", "priority"}
        fields, params = [], []
        for key in allowed:
            if key in payload:
                fields.append(f"{key} = ?")
                params.append(payload[key])
        if not fields:
            return current
        if "status" in payload and payload["status"] not in {"todo", "running", "done", "blocked"}:
            raise ValidationError("status 取值非法")
        fields.append("updated_at = datetime('now')")
        params.append(task_id)
        with self.db.transaction() as tx:
            tx.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id=?", tuple(params))
        return self.get(task_id)

    def delete(self, task_id: int) -> None:
        self.get(task_id)
        with self.db.transaction() as tx:
            tx.execute("DELETE FROM tasks WHERE id=?", (task_id,))

    def plan(self, task_id: int) -> dict[str, Any]:
        """返回该任务的分级规划（层级子任务树）。"""
        task = self.get(task_id)
        steps = [dict(r) for r in self.db.query(
            "SELECT * FROM plan_steps WHERE task_id=? ORDER BY step_no", (task_id,))]
        return {"task": task, "level": task["level"], "label": LEVEL_LABEL[task["level"]],
                "steps": steps, "total_minutes": sum(s["est_minutes"] for s in steps)}

    def record_run(self, task_id: int, agent_name: str, outcome: str,
                   latency_ms: int = 0, retries: int = 0) -> dict[str, Any]:
        """记录一次 Agent 执行；失败时自动标记任务为 blocked（失效升级）。"""
        self.get(task_id)
        if outcome not in {"success", "failure", "escalated"}:
            raise ValidationError("outcome 取值非法")
        with self.db.transaction() as tx:
            tx.execute(
                "INSERT INTO agent_runs(task_id,agent_name,outcome,latency_ms,retries) VALUES(?,?,?,?,?)",
                (task_id, agent_name, outcome, max(0, latency_ms), max(0, retries)),
            )
            if outcome == "escalated":
                tx.execute("UPDATE tasks SET status='blocked', updated_at=datetime('now') WHERE id=?", (task_id,))
        return {"task_id": task_id, "agent_name": agent_name, "outcome": outcome,
                "escalated": outcome == "escalated"}

    def runs(self, task_id: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT r.*, t.title AS task_title FROM agent_runs r JOIN tasks t ON t.id=r.task_id"
        params: tuple = ()
        if task_id:
            sql += " WHERE r.task_id=?"; params = (task_id,)
        sql += " ORDER BY r.id DESC LIMIT 200"
        return [dict(r) for r in self.db.query(sql, params)]


class AnalysisService:
    def __init__(self, db: Database):
        self.db = db

    def overview(self) -> dict[str, Any]:
        tasks = self.db.query("SELECT status, level FROM tasks")
        defects = self.db.query("SELECT severity, cause_type FROM defects")
        runs = self.db.query("SELECT outcome FROM agent_runs")
        total = len(tasks) or 1
        o = {
            "total_tasks": len(tasks),
            "done_tasks": sum(1 for t in tasks if t["status"] == "done"),
            "running_tasks": sum(1 for t in tasks if t["status"] == "running"),
            "blocked_tasks": sum(1 for t in tasks if t["status"] == "blocked"),
            "total_defects": len(defects),
            "l1_count": sum(1 for t in tasks if t["level"] == "L1"),
            "l2_count": sum(1 for t in tasks if t["level"] == "L2"),
            "l3_count": sum(1 for t in tasks if t["level"] == "L3"),
            "completion_rate": round(sum(1 for t in tasks if t["status"] == "done") / total * 100, 1),
            "agent_success_rate": 0.0,
        }
        if runs:
            o["agent_success_rate"] = round(sum(1 for r in runs if r["outcome"] == "success") / len(runs) * 100, 1)
        return o

    def pareto(self) -> dict[str, Any]:
        """缺陷帕累托：按类别统计频次并计算累计占比。"""
        rows = self.db.query("SELECT category, COUNT(*) AS n FROM defects GROUP BY category ORDER BY n DESC, category")
        total = sum(r["n"] for r in rows) or 1
        cumulative, items = 0, []
        for r in rows:
            cumulative += r["n"]
            items.append({"category": r["category"], "count": r["n"],
                          "percent": round(r["n"] / total * 100, 1),
                          "cumulative": round(cumulative / total * 100, 1)})
        vital_few = [i["category"] for i in items if i["cumulative"] <= 80]
        if not vital_few and items:
            vital_few = [items[0]["category"]]
        return {"items": items, "total": total, "vital_few": vital_few}

    def failure_scores(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT f.*, t.title, t.level FROM failure_scores f JOIN tasks t ON t.id=f.task_id ORDER BY f.score ASC")
        return [dict(r) for r in rows]

    def reliability(self) -> dict[str, Any]:
        scores = [r["score"] for r in self.db.query("SELECT score FROM failure_scores")]
        if not scores:
            return {"average": 0.0, "grade": "N/A", "distribution": {}, "sample_size": 0}
        avg = sum(scores) / len(scores)
        dist = Counter("A" if s >= 90 else "B" if s >= 80 else "C" if s >= 70 else "D" for s in scores)
        return {
            "average": round(avg, 1),
            "grade": "A" if avg >= 90 else "B" if avg >= 80 else "C" if avg >= 70 else "D",
            "distribution": {k: dist.get(k, 0) for k in "ABCD"},
            "sample_size": len(scores),
        }

    @staticmethod
    def compute_failure_score(defect_weights: list[tuple[str, float]], base: float = 96.0) -> dict[str, Any]:
        """失效评分公式（可解释）：score = base - Σ(严重度权重 × 归因系数)。

        严重度权重：critical=18, major=9, minor=3；
        归因系数：agent=1.0, tool=0.7, human=0.5, requirement=0.6。
        """
        sev_w = {"critical": 18.0, "major": 9.0, "minor": 3.0}
        cause_w = {"agent": 1.0, "tool": 0.7, "human": 0.5, "requirement": 0.6}
        penalty = 0.0
        detail = []
        for sev, cause in defect_weights:
            sw = sev_w.get(sev, 3.0)
            cw = cause_w.get(cause, 0.5)
            penalty += sw * cw
            detail.append({"severity": sev, "cause": cause, "penalty": round(sw * cw, 2)})
        score = round(max(0.0, min(100.0, base - penalty)), 1)
        grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D"
        return {"score": score, "grade": grade, "base": base,
                "penalty": round(penalty, 2), "detail": detail}
