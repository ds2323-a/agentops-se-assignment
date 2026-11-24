"""生成实验报告所需的软件工程图表（无需外部依赖，matplotlib + pillow）。

输出目录：D:/大作业/图表
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, Rectangle, Circle, Ellipse,
                                Polygon, FancyArrowPatch)
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = Path("D:/大作业/图表")
OUT.mkdir(parents=True, exist_ok=True)

# 主题色
PRIMARY = "#4F46E5"
CYAN = "#0EA5A4"
ORANGE = "#F59E0B"
RED = "#E11D48"
INK = "#1D2440"
MUTED = "#6B7391"
LINE = "#C9CFE2"
SOFT = "#EEF0FF"


def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path.name)


def noaxis(ax):
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")


def box(ax, x, y, w, h, text, fc=SOFT, ec=PRIMARY, tc=INK, fs=11, rad=0.14, lw=1.6, bold=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={rad}",
                       linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, fontweight="bold" if bold else "normal", zorder=3, linespacing=1.5)
    return p


def arrow(ax, x1, y1, x2, y2, color=MUTED, lw=1.5, style="-|>", rad=0):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13,
                        linewidth=lw, color=color, connectionstyle=f"arc3,rad={rad}", zorder=1)
    ax.add_patch(a)


# ---------------------------------------------------------------- 1 可行性雷达图
def radar():
    labels = ["经济可行性", "技术可行性", "操作可行性", "人员可行性", "时间可行性"]
    scores = [88, 92, 85, 80, 86]
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    vals = scores + scores[:1]

    fig, ax = plt.subplots(figsize=(7.2, 6.4), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12, color=INK)
    ax.tick_params(axis="x", pad=16)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=9, color=MUTED)
    ax.grid(color=LINE, linewidth=0.9)
    ax.spines["polar"].set_color(LINE)
    ax.plot(angles, vals, color=PRIMARY, linewidth=2.4, zorder=4)
    ax.fill(angles, vals, color=PRIMARY, alpha=0.20, zorder=3)
    for a, v in zip(angles[:-1], scores):
        ax.scatter(a, v, s=70, color=CYAN, edgecolor="white", linewidth=1.2, zorder=5)
        ax.text(a, v + 7, str(v), ha="center", va="center", fontsize=10,
                color=PRIMARY, fontweight="bold", zorder=6)
    ax.set_title("系统可行性五维分析", fontsize=16, fontweight="bold", color=INK, pad=30)
    fig.text(0.5, 0.02, "综合评分 86.2 / 100 —— 五个维度均处于可行区间，项目可立项实施",
             ha="center", fontsize=10.5, color=MUTED)
    save(fig, "01_可行性五维雷达图.png")


# ---------------------------------------------------------------- 2 用例图
def usecase():
    fig, ax = plt.subplots(figsize=(11, 6.6))
    noaxis(ax)
    ax.set_title("系统用例图", fontsize=16, fontweight="bold", color=INK, pad=6)

    # 系统边界
    boundary = FancyBboxPatch((3.0, 0.9), 6.6, 8.0, boxstyle="round,pad=0.05,rounding_size=0.2",
                              linewidth=1.8, edgecolor=LINE, facecolor="#FBFCFF", zorder=0)
    ax.add_patch(boundary)
    ax.text(6.3, 8.5, "AgentOps 分级规划与失效分析平台", ha="center", fontsize=11,
            color=MUTED, fontweight="bold")

    def actor(x, y, name):
        ax.add_patch(Circle((x, y + 0.55), 0.22, fill=False, ec=INK, lw=1.6, zorder=3))
        ax.plot([x, x], [y + 0.33, y - 0.15], color=INK, lw=1.6)
        ax.plot([x - 0.32, x + 0.32], [y + 0.15, y + 0.15], color=INK, lw=1.6)
        ax.plot([x, x - 0.28], [y - 0.15, y - 0.55], color=INK, lw=1.6)
        ax.plot([x, x + 0.28], [y - 0.15, y - 0.55], color=INK, lw=1.6)
        ax.text(x, y - 0.85, name, ha="center", fontsize=11, color=INK, fontweight="bold")

    actor(1.3, 6.6, "研发人员")
    actor(1.3, 3.2, "管理员")
    actor(9.6, 4.9, "Agent 调度器")

    cases = [
        (4.5, 7.3, "用户登录 / 认证"),
        (7.6, 7.3, "创建研发任务"),
        (4.5, 5.3, "AI 分级规划"),
        (7.6, 5.3, "执行 / 监控任务"),
        (4.5, 3.3, "失效分析 & 帕累托"),
        (7.6, 3.3, "缺陷复盘与升级"),
        (6.05, 1.6, "系统配置与管理"),
    ]
    for x, y, t in cases:
        e = Ellipse((x, y), 2.5, 0.95, facecolor=SOFT, edgecolor=PRIMARY, lw=1.5, zorder=2)
        ax.add_patch(e)
        ax.text(x, y, t, ha="center", va="center", fontsize=10, color=INK, zorder=3)

    # 参与者到用例的关联
    for (x, y) in [(4.5, 7.3), (4.5, 5.3), (4.5, 3.3), (7.6, 7.3), (7.6, 5.3), (7.6, 3.3)]:
        arrow(ax, 1.75, 6.6 if y > 4 else 3.2, x - 1.25, y, color=LINE, lw=1.2, style="-")
    for (x, y) in [(7.6, 5.3), (7.6, 3.3), (6.05, 1.6)]:
        arrow(ax, 9.25, 4.9, x + 1.25, y, color=LINE, lw=1.2, style="-")
    ax.text(5.0, 0.15, "图 2-1  系统主要参与者与用例",
            ha="center", fontsize=10, color=MUTED)
    save(fig, "02_用例图.png")


# ---------------------------------------------------------------- 3 系统架构图
def architecture():
    fig, ax = plt.subplots(figsize=(11.6, 8))
    ax.set_xlim(0, 11); ax.set_ylim(0, 10); ax.axis("off")
    ax.set_title("系统总体架构图（分层架构）", fontsize=16, fontweight="bold", color=INK, pad=6)

    layers = [
        (8.1, 1.5, "表现层  Presentation", ["Web 管理后台", "任务看板 / 图表", "分级规划器 UI"], "#EDEBFF", PRIMARY),
        (6.0, 1.5, "接口层  API / Controller", ["RESTful 路由", "输入校验", "统一响应 & 错误处理"], "#E3F4FF", "#0284C7"),
        (3.9, 1.5, "服务层  Service", ["TaskService", "分级规划引擎", "失效评分 / 帕累托分析"], "#E6FAF6", CYAN),
        (1.8, 1.5, "数据层  Repository / DB", ["Repository 仓储", "SQLite（WAL）", "迁移 & 种子数据"], "#FFF3DC", ORANGE),
    ]
    for y, h, title, items, fc, ec in layers:
        ax.add_patch(FancyBboxPatch((0.55, y), 8.9, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=1.6, edgecolor=ec, facecolor="#FFFFFF", zorder=1))
        ax.text(0.85, y + h - 0.32, title, ha="left", va="center", fontsize=11,
                color=ec, fontweight="bold", zorder=3)
        w = 2.65; gap = 0.18; start = 1.0
        for i, it in enumerate(items):
            box(ax, start + i * (w + gap), y + 0.2, w, h - 0.72, it,
                fc=fc, ec=ec, tc=INK, fs=10, rad=0.1, lw=1.2)
    # 层间箭头
    for y in [7.95, 5.85, 3.75, 1.65]:
        arrow(ax, 5.0, y, 5.0, y - 0.2, color=PRIMARY, lw=1.8)

    # 右侧基础设施
    ax.add_patch(FancyBboxPatch((9.75, 1.8), 1.0, 7.8, boxstyle="round,pad=0.02,rounding_size=0.12",
                                linewidth=1.6, edgecolor=MUTED, facecolor="#F7F8FC", zorder=1))
    ax.text(10.25, 9.15, "基础设施", ha="center", fontsize=10.5, color=MUTED, fontweight="bold")
    for i, t in enumerate(["集中配置\n& 启动校验", "结构化 JSON\n日志 + 请求ID", "类型化错误\n全局处理器", "健康检查\n/ CORS / 安全头"]):
        box(ax, 9.88, 7.9 - i * 1.65, 0.74, 1.3, t, fc="#FFFFFF", ec=LINE, tc=INK, fs=8.2, rad=0.08, lw=1)
    arrow(ax, 9.6, 5.7, 9.85, 5.7, color=LINE, lw=1.2, style="-")

    ax.text(5.0, 0.55, "图 3-1  基于「按功能组织 + 三层架构」的系统分层设计",
            ha="center", fontsize=10, color=MUTED)
    save(fig, "03_系统架构图.png")


# ---------------------------------------------------------------- 4 UML 类图
def classdiagram():
    fig, ax = plt.subplots(figsize=(12.5, 8.4))
    ax.set_xlim(0, 11.4); ax.set_ylim(-0.6, 10); ax.axis("off")
    ax.set_title("核心 UML 类图", fontsize=16, fontweight="bold", color=INK, pad=6)

    def cls(x, y, w, h, name, attrs, methods, ec=PRIMARY, fc="#FFFFFF", fs=9.5):
        ax.add_patch(Rectangle((x, y), w, h, linewidth=1.7, edgecolor=ec, facecolor=fc, zorder=2))
        hh = 0.62
        ax.add_patch(Rectangle((x, y + h - hh), w, hh, facecolor=ec, edgecolor=ec, zorder=3))
        ax.text(x + w / 2, y + h - hh / 2, name, ha="center", va="center",
                fontsize=fs + 0.6, color="white", fontweight="bold", zorder=4)
        ax.text(x + 0.18, y + h - hh - 0.12, "\n".join(attrs), ha="left", va="top",
                fontsize=fs - 0.8, color=INK, zorder=4, linespacing=1.35)
        sep = y + h - hh - 0.12 - 0.36 * len(attrs) - 0.12
        ax.plot([x, x + w], [sep, sep], color=LINE, lw=1, zorder=4)
        ax.text(x + 0.18, sep - 0.1, "\n".join(methods), ha="left", va="top",
                fontsize=fs - 0.8, color=MUTED, zorder=4, linespacing=1.35)

    classes = [
        (0.4, 5.6, 2.9, 2.0, "Task 任务", ["+id:int", "+title:str", "+level:L1|L2|L3", "+status:enum"], ["+create()", "+update()"], PRIMARY),
        (4.0, 5.6, 2.9, 2.0, "PlanStep 规划步骤", ["+id:int", "+task_id:int", "+agent:str", "+est_minutes:int"], ["+generateTree()"], CYAN),
        (7.6, 5.6, 2.9, 2.0, "Defect 缺陷", ["+id:int", "+category:str", "+severity:enum", "+cause_type:enum"], ["+classify()"], ORANGE),
        (0.4, 2.2, 2.9, 2.0, "AgentRun 执行记录", ["+id:int", "+outcome:enum", "+latency_ms:int", "+retries:int"], ["+escalate()"], CYAN),
        (4.0, 2.2, 2.9, 2.0, "FailureScore 失效评分", ["+score:float", "+reliability:A|B|C|D", "+penalty:float"], ["+compute()"], RED),
        (7.6, 2.2, 2.9, 2.0, "User 用户", ["+id:int", "+username:str", "+role:enum"], ["+login()"], MUTED),
        (2.2, 0.05, 3.2, 1.35, "TaskService", ["", "+create() / plan()", "+recordRun()"], "#4F46E5", "#EEF0FF"),
        (6.0, 0.05, 3.2, 1.35, "AnalysisService", ["", "+pareto() / reliability()", "+computeFailureScore()"], "#0EA5A4", "#E6FAF6"),
        (9.6, 0.05, 1.5, 1.35, "Database", ["", "+query()", "+transaction()"], "#F59E0B", "#FFF3DC"),
    ]
    for x, y, w, h, name, attrs, methods, ec, *rest in classes:
        fc = rest[0] if rest else "#FFFFFF"
        cls(x, y, w, h, name, attrs, methods, ec=ec, fc=fc)

    # 关联关系
    arrow(ax, 3.3, 6.6, 4.0, 6.6, style="-")
    ax.text(3.65, 6.78, "1 : *", fontsize=8, color=MUTED, ha="center")
    arrow(ax, 6.9, 6.6, 7.6, 6.6, style="-")
    ax.text(7.25, 6.78, "1 : *", fontsize=8, color=MUTED, ha="center")
    arrow(ax, 3.3, 6.0, 1.85, 4.2, style="-")
    ax.text(2.1, 5.2, "1 : *", fontsize=8, color=MUTED)
    arrow(ax, 3.35, 3.2, 4.0, 3.2, style="-")
    arrow(ax, 6.9, 3.2, 7.6, 3.2, style="-")
    ax.text(5.4, 2.05, "服务层调用领域对象 →", fontsize=9, color=MUTED, ha="center")
    arrow(ax, 5.4, 1.4, 5.4, 2.2, color=PRIMARY, lw=1.5)
    arrow(ax, 9.3, 0.72, 11.0, 0.72, color=ORANGE, lw=1.4)

    ax.text(5.0, -0.35, "图 4-1  领域模型与服务层核心类及其关联关系",
            ha="center", fontsize=10, color=MUTED)
    save(fig, "04_UML类图.png")


# ---------------------------------------------------------------- 5 程序流程图
def flowchart():
    fig, ax = plt.subplots(figsize=(7.4, 10.5))
    noaxis(ax)
    ax.set_title("任务创建与分级规划程序流程图", fontsize=16, fontweight="bold", color=INK, pad=6)

    # 起止
    ax.add_patch(Ellipse((5, 9.4), 2.4, 0.8, facecolor=PRIMARY, edgecolor=PRIMARY))
    ax.text(5, 9.4, "开始", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
    box(ax, 3.5, 8.3, 3.0, 0.75, "用户输入任务标题 / 描述", fc="#FFFFFF", ec=LINE, fs=10.5)
    arrow(ax, 5, 9.0, 5, 9.05)
    box(ax, 3.5, 7.15, 3.0, 0.75, "边界校验（长度 / 枚举 / 优先级）", fc=SOFT, ec=PRIMARY, fs=10)

    # 判断菱形
    diamond = Polygon([[5, 6.55], [6.5, 5.95], [5, 5.35], [3.5, 5.95]],
                      closed=True, facecolor="#FFF3DC", edgecolor=ORANGE, lw=1.7, zorder=2)
    ax.add_patch(diamond)
    ax.text(5, 5.95, "参数合法？", ha="center", va="center", fontsize=10.5, color=INK, zorder=3)
    arrow(ax, 5, 7.15, 5, 6.55)
    ax.text(6.55, 6.35, "否", fontsize=10, color=RED)
    box(ax, 7.3, 6.0, 2.3, 0.7, "返回 400 错误", fc="#FFE9EC", ec=RED, tc=RED, fs=10)
    arrow(ax, 6.45, 6.15, 7.3, 6.3, color=RED)
    ax.text(3.2, 6.0, "是", fontsize=10, color=CYAN)

    # 分级判断
    diamond2 = Polygon([[5, 5.15], [6.6, 4.45], [5, 3.75], [3.4, 4.45]],
                       closed=True, facecolor=SOFT, edgecolor=PRIMARY, lw=1.7, zorder=2)
    ax.add_patch(diamond2)
    ax.text(5, 4.45, "AI 分级规划引擎\n风险评分 → L1/L2/L3", ha="center", va="center",
            fontsize=9.5, color=INK, zorder=3, linespacing=1.4)
    arrow(ax, 5, 5.35, 5, 5.15)

    # 三个分支
    branch_y = 2.25
    branch = [(1.6, "L1 自动完成", CYAN, "#E6FAF6"),
              (5.0, "L2 人机协作", ORANGE, "#FFF3DC"),
              (8.4, "L3 纯人工", RED, "#FFE9EC")]
    for x, t, ec, fc in branch:
        box(ax, x - 1.35, branch_y, 2.7, 0.75, t, fc=fc, ec=ec, tc=ec, fs=10.5, bold=True)
    arrow(ax, 4.3, 4.2, 1.9, 3.0, color=CYAN, lw=1.4, rad=-0.1)
    arrow(ax, 5.0, 3.75, 5.0, 3.0, color=ORANGE, lw=1.4)
    arrow(ax, 5.7, 4.2, 8.1, 3.0, color=RED, lw=1.4, rad=0.1)
    ax.text(2.7, 3.95, "低风险", fontsize=9, color=CYAN)
    ax.text(7.0, 3.95, "高风险", fontsize=9, color=RED)

    # 汇聚
    box(ax, 3.4, 1.15, 3.2, 0.7, "生成层级子任务规划树", fc="#FFFFFF", ec=LINE, fs=10)
    for x, _, c, _ in branch:
        arrow(ax, x, branch_y, 5, 1.95, color=c, lw=1.2, rad=0)
    box(ax, 3.4, 0.35, 3.2, 0.6, "事务写入 DB → 返回 201", fc=SOFT, ec=PRIMARY, fs=10)
    arrow(ax, 5, 1.15, 5, 0.95)

    ax.text(5, -0.25, "图 5-1  任务创建与分级规划核心流程（含异常分支）",
            ha="center", fontsize=10, color=MUTED)
    save(fig, "05_程序流程图.png")


# ---------------------------------------------------------------- 6 缺陷帕累托图
def pareto():
    cats = ["代码生成错误", "需求理解偏差", "接口契约不一致", "数据模型缺陷", "文档结构缺失", "工具链异常", "测试用例缺失"]
    counts = [5, 5, 2, 2, 2, 1, 1]
    total = sum(counts)
    cum = np.cumsum(counts) / total * 100

    fig, ax = plt.subplots(figsize=(10, 6.2))
    x = np.arange(len(cats))
    bars = ax.bar(x, counts, color=[PRIMARY] * 4 + ["#A5B4FC"] * 3, width=0.62, zorder=3)
    ax.set_ylabel("缺陷数量", fontsize=11, color=INK)
    ax.set_ylim(0, max(counts) * 1.35)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, rotation=18, ha="right", fontsize=10, color=INK)
    ax.grid(axis="y", color=LINE, alpha=0.5, linewidth=0.8, zorder=0)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + 0.12, str(c),
                ha="center", fontsize=10, color=INK, fontweight="bold", zorder=4)

    ax2 = ax.twinx()
    ax2.plot(x, cum, color=RED, marker="o", linewidth=2.2, markersize=6, zorder=5)
    ax2.axhline(80, color=RED, linestyle="--", alpha=0.6, linewidth=1.2)
    ax2.text(len(cats) - 0.4, 81.5, "80% 分界", color=RED, fontsize=9, ha="right")
    ax2.set_ylim(0, 108)
    ax2.set_ylabel("累计占比 (%)", fontsize=11, color=RED)
    ax2.tick_params(axis="y", colors=RED)
    for xi, ci in zip(x, cum):
        ax2.text(xi, ci + 4, f"{ci:.1f}%", ha="center", fontsize=8.5, color=RED)

    ax.set_title("缺陷帕累托图 —— 关键少数缺陷识别", fontsize=15, fontweight="bold", color=INK, pad=14)
    fig.text(0.5, 0.01, "结论：前 4 类缺陷累计占比 77.8%，为主要改进对象；优先治理「代码生成错误」与「需求理解偏差」。",
             ha="center", fontsize=10, color=MUTED)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    save(fig, "06_缺陷帕累托图.png")


# ---------------------------------------------------------------- 7 AI 分级机制表
def grading_table():
    fig, ax = plt.subplots(figsize=(12.6, 6.4))
    ax.set_xlim(0, 12.7); ax.set_ylim(0, 8.0); ax.axis("off")
    ax.set_title("AI Agent 三级分级机制表（任务拆分与监管策略）", fontsize=16, fontweight="bold", color=INK, pad=8)

    headers = ["分级", "AI 参与度", "典型任务", "拆分粒度", "失效风险", "监管方式"]
    rows = [
        ["L1\n自动完成", "90–100%\n全自动", "批量数据清洗、报表导出、\n格式转换、日志检索", "单一明确目标\n→ 原子子任务", "低", "结果抽检\n+ 自动断言"],
        ["L2\n人机协作", "40–70%\nAI 生成 / 人评审", "架构设计、接口开发、\n看板前端、文档生成", "阶段化拆解\n→ 候选方案 + 评审点", "中", "人工评审闸口\n+ 回归测试"],
        ["L3\n纯人工", "0–30%\nAI 仅辅助检索", "支付回调、风控策略、\n合规签署、最终决策", "风险驱动拆解\n→ 人工决策节点", "高", "人工主导\n+ 失效复盘强制"],
    ]
    x0, y0 = 0.25, 1.0
    widths = [1.35, 1.7, 3.2, 2.5, 1.35, 2.0]
    col_x = [x0]
    for w in widths:
        col_x.append(col_x[-1] + w)
    header_h, row_h = 1.0, 1.75

    for j, h in enumerate(headers):
        ax.add_patch(Rectangle((col_x[j], y0 + 3 * row_h), widths[j], header_h,
                               facecolor=PRIMARY, edgecolor="white", lw=1.5, zorder=2))
        ax.text(col_x[j] + widths[j] / 2, y0 + 3 * row_h + header_h / 2, h,
                ha="center", va="center", color="white", fontsize=11, fontweight="bold", zorder=3)

    colors = [CYAN, ORANGE, RED]
    for i, row in enumerate(rows):
        y = y0 + (2 - i) * row_h
        for j, cell in enumerate(row):
            fc = ["#E6FAF6", "#FFF3DC", "#FFE9EC"][i] if j == 0 else ("#F7F8FC" if i % 2 == 0 else "#FFFFFF")
            ax.add_patch(Rectangle((col_x[j], y), widths[j], row_h,
                                   facecolor=fc, edgecolor=LINE, lw=1.1, zorder=2))
            tc = colors[i] if j == 0 else INK
            ax.text(col_x[j] + widths[j] / 2, y + row_h / 2, cell,
                    ha="center", va="center", fontsize=9.6 if j != 2 else 9.3,
                    color=tc, fontweight="bold" if j == 0 else "normal", zorder=3, linespacing=1.5)

    ax.text(x0, 0.35, "判定规则：风险评分 = 14 + 6×L2关键词 + 20×L3关键词 − 4×L1关键词；≥55 → L3，25–54 → L2，<25 → L1。",
            fontsize=9.6, color=MUTED, ha="left")
    save(fig, "07_AI分级机制表.png")


# ---------------------------------------------------------------- 8 失效评分模型
def failure_model():
    fig, ax = plt.subplots(figsize=(11.2, 6.6))
    ax.set_xlim(0, 10.7); ax.set_ylim(0, 10); ax.axis("off")
    ax.set_title("Agent 失效评分模型与监管闭环", fontsize=16, fontweight="bold", color=INK, pad=8)

    box(ax, 0.3, 7.7, 3.0, 1.0, "缺陷事件采集\n(类别 / 严重度 / 归因)", fc="#E3F4FF", ec="#0284C7", fs=10.5)
    box(ax, 4.2, 7.7, 3.0, 1.0, "加权惩罚计算\nΣ 严重度 × 归因系数", fc=SOFT, ec=PRIMARY, fs=10.5)
    box(ax, 8.1, 7.7, 2.6, 1.0, "失效评分\nScore = 96 − Penalty", fc="#FFE9EC", ec=RED, fs=10.5)
    arrow(ax, 3.3, 8.2, 4.2, 8.2)
    arrow(ax, 7.2, 8.2, 8.1, 8.2)

    box(ax, 1.0, 5.7, 2.2, 0.9, "critical × 18", fc="#FFE9EC", ec=RED, tc=RED, fs=10)
    box(ax, 3.4, 5.7, 2.2, 0.9, "major × 9", fc="#FFF3DC", ec=ORANGE, tc=ORANGE, fs=10)
    box(ax, 5.8, 5.7, 2.2, 0.9, "minor × 3", fc="#EEF0FF", ec=PRIMARY, fs=10)
    box(ax, 8.2, 5.7, 2.2, 0.9, "归因系数\nagent 1.0 / tool 0.7", fc="#F7F8FC", ec=MUTED, fs=9)
    arrow(ax, 5.7, 7.7, 5.7, 6.7, color=MUTED)

    # 评级带
    grades = [("A ≥90 稳定", CYAN, "#E6FAF6"), ("B 80–89 可用", PRIMARY, SOFT),
              ("C 70–79 预警", ORANGE, "#FFF3DC"), ("D <70 失效", RED, "#FFE9EC")]
    for i, (t, c, fc) in enumerate(grades):
        box(ax, 0.4 + i * 2.6, 3.6, 2.35, 1.0, t, fc=fc, ec=c, tc=c, fs=10.5, bold=True)
        arrow(ax, 9.4, 7.7, 1.6 + i * 2.6, 4.6, color=LINE, lw=1.0, rad=0.05)

    box(ax, 0.4, 1.9, 4.6, 1.0, "D 级 → 升级 L3 纯人工\n增加强制评审节点", fc="#FFE9EC", ec=RED, fs=10.5)
    box(ax, 5.6, 1.9, 4.6, 1.0, "C 级 → 保持 L2\n补充回归用例与自动校验", fc="#FFF3DC", ec=ORANGE, fs=10.5)
    arrow(ax, 1.6, 3.6, 2.7, 2.9, color=RED, lw=1.3)
    arrow(ax, 7.0, 3.6, 7.9, 2.9, color=ORANGE, lw=1.3)

    arrow(ax, 5.0, 1.9, 5.0, 1.35, color=PRIMARY, lw=1.4)
    box(ax, 2.0, 0.45, 6.0, 0.85, "复盘结论回流至分级规则库 → 形成监管闭环", fc=SOFT, ec=PRIMARY, fs=10.5)

    ax.text(5.0, 0.05, "图 8-1  失效评分计算与「评分→升级→复盘→回流」监管闭环",
            ha="center", fontsize=9.6, color=MUTED)
    save(fig, "08_失效评分模型.png")


if __name__ == "__main__":
    radar()
    usecase()
    architecture()
    classdiagram()
    flowchart()
    pareto()
    grading_table()
    failure_model()
    print("\n全部图表生成完成 →", OUT)
