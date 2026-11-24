"""控制器层：解析请求 → 调用服务 → 格式化响应，不写业务逻辑。"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from .errors import NotFoundError, UnauthorizedError, ValidationError
from .services import AnalysisService, TaskService, classify_text

DEMO_USERS = {"admin": "admin123", "alice": "alice123", "bob": "bob123"}


class Router:
    def __init__(self, task_service: TaskService, analysis_service: AnalysisService):
        self.tasks = task_service
        self.analysis = analysis_service

    def dispatch(self, method: str, path: str, query: dict[str, list[str]],
                 body: dict[str, Any] | None, request_id: str) -> tuple[int, Any]:
        q = {k: v[0] for k, v in query.items() if v}
        body = body or {}

        # 健康检查（无需认证）
        if method == "GET" and path == "/health":
            return 200, {"status": "ok", "request_id": request_id}
        if method == "GET" and path == "/ready":
            return 200, {"status": "ready", "checks": {"database": "ok"}, "request_id": request_id}

        # 演示认证
        if method == "POST" and path == "/api/auth/login":
            username = str(body.get("username") or "")
            password = str(body.get("password") or "")
            if DEMO_USERS.get(username) != password:
                raise UnauthorizedError("用户名或密码错误")
            return 200, {"token": f"demo-{username}", "username": username,
                         "display_name": {"admin": "系统管理员", "alice": "Alice", "bob": "Bob"}.get(username, username)}

        # 分级规划器（无状态）
        if method == "POST" and path == "/api/planning/classify":
            title = str(body.get("title") or "").strip()
            if not title:
                raise ValidationError("title 不能为空")
            return 200, classify_text(title, str(body.get("description") or ""))

        # 任务 CRUD
        if method == "GET" and path == "/api/tasks":
            return 200, {"items": self.tasks.list(
                status=q.get("status"), level=q.get("level"), project=q.get("project"),
                limit=int(q.get("limit", 100)) if q.get("limit", "100").isdigit() else 100)}
        if method == "POST" and path == "/api/tasks":
            return 201, self.tasks.create(body)
        if path.startswith("/api/tasks/"):
            parts = path.strip("/").split("/")   # ['api','tasks','<id>', ...]
            if len(parts) < 3:
                raise NotFoundError()
            task_id = self._id(parts[2])
            if len(parts) == 3:
                if method == "GET":
                    return 200, self.tasks.get(task_id)
                if method == "PATCH":
                    return 200, self.tasks.update(task_id, body)
                if method == "DELETE":
                    self.tasks.delete(task_id)
                    return 204, None
            if len(parts) == 4 and parts[3] == "plan" and method == "GET":
                return 200, self.tasks.plan(task_id)
            if len(parts) == 4 and parts[3] == "runs":
                if method == "GET":
                    return 200, {"items": self.tasks.runs(task_id)}
                if method == "POST":
                    return 201, self.tasks.record_run(
                        task_id, str(body.get("agent_name") or "Coder-Agent"),
                        str(body.get("outcome") or "success"),
                        int(body.get("latency_ms") or 0), int(body.get("retries") or 0))

        # 分析
        if method == "GET" and path == "/api/analysis/overview":
            return 200, self.analysis.overview()
        if method == "GET" and path == "/api/analysis/pareto":
            return 200, self.analysis.pareto()
        if method == "GET" and path == "/api/analysis/failure-scores":
            return 200, {"items": self.analysis.failure_scores()}
        if method == "GET" and path == "/api/analysis/reliability":
            return 200, self.analysis.reliability()
        if method == "GET" and path == "/api/agent-runs":
            return 200, {"items": self.tasks.runs()}

        raise NotFoundError(f"未知端点: {method} {path}")

    @staticmethod
    def _id(value: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ValidationError("任务 ID 必须为整数") from exc
