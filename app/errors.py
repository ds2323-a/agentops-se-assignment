"""类型化错误体系与规范化错误码。"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    status = 500
    code = "INTERNAL_ERROR"
    message = "服务器内部错误"

    def __init__(self, message: str | None = None, **details: Any):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"ok": False, "code": self.code, "message": self.message}
        if self.details:
            body["details"] = self.details
        return body


class ValidationError(AppError):
    status = 400
    code = "VALIDATION_ERROR"
    message = "请求参数不合法"


class NotFoundError(AppError):
    status = 404
    code = "NOT_FOUND"
    message = "资源不存在"


class ConflictError(AppError):
    status = 409
    code = "CONFLICT"
    message = "资源冲突"


class UnauthorizedError(AppError):
    status = 401
    code = "UNAUTHORIZED"
    message = "未认证或凭证失效"


class AgentExecutionError(AppError):
    status = 422
    code = "AGENT_EXECUTION_FAILED"
    message = "Agent 执行失败"
