"""HTTP 服务：全局错误处理、CORS、请求 ID、静态资源。"""
from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .config import Settings, load_settings
from .controllers import Router
from .db import Database
from .errors import AppError
from .logging_util import error as log_error
from .logging_util import info
from .services import AnalysisService, TaskService

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentOps/1.0"
    router: Router
    settings: Settings

    def log_message(self, fmt: str, *args) -> None:
        pass  # 使用结构化日志替代

    def _request_id(self) -> str:
        return self.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]

    def _cors(self, request_id: str) -> None:
        origin = self.headers.get("Origin", "")
        if origin in self.settings.cors_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("X-Request-ID", request_id)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def _send_json(self, status: int, payload, request_id: str) -> None:
        data = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors(request_id)
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _send_static(self, name: str, request_id: str) -> None:
        target = name.lstrip("/") or "index.html"
        path = (WEB_DIR / target).resolve()
        if not str(path).startswith(str(WEB_DIR.resolve())) or not path.is_file():
            self._send_json(404, {"ok": False, "code": "NOT_FOUND", "message": "页面不存在"}, request_id)
            return
        mime = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8", ".png": "image/png",
                ".svg": "image/svg+xml"}.get(path.suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self._cors(request_id)
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
            return value if isinstance(value, dict) else {}
        except (ValueError, UnicodeDecodeError):
            from .errors import ValidationError
            raise ValidationError("请求体必须是合法 JSON 对象")

    def _handle(self, method: str) -> None:
        rid = self._request_id()
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        try:
            if method == "OPTIONS":
                self._send_json(204, None, rid)
                return
            if not path.startswith("/api/") and path not in {"/health", "/ready"}:
                if method == "GET":
                    self._send_static(path, rid)
                else:
                    self._send_json(405, {"ok": False, "code": "METHOD_NOT_ALLOWED", "message": "方法不允许"}, rid)
                return
            body = self._body() if method in {"POST", "PATCH", "PUT"} else None
            status, payload = self.router.dispatch(method, path, query, body, rid)
            self._send_json(status, payload, rid)
            info("request", rid, method=method, path=path, status=status)
        except AppError as exc:
            self._send_json(exc.status, exc.to_dict(), rid)
            log_error("request_error", rid, method=method, path=path, code=exc.code, status=exc.status)
        except Exception as exc:  # noqa: BLE001 - 全局兜底，绝不返回堆栈
            self._send_json(500, {"ok": False, "code": "INTERNAL_ERROR", "message": "服务器内部错误"}, rid)
            log_error("unhandled_error", rid, method=method, path=path, exc_type=type(exc).__name__)

    def do_GET(self) -> None: self._handle("GET")
    def do_POST(self) -> None: self._handle("POST")
    def do_PATCH(self) -> None: self._handle("PATCH")
    def do_DELETE(self) -> None: self._handle("DELETE")
    def do_OPTIONS(self) -> None: self._handle("OPTIONS")


def build_server(settings: Settings | None = None) -> ThreadingHTTPServer:
    settings = settings or load_settings()
    db = Database(settings)
    task_service = TaskService(db)
    analysis_service = AnalysisService(db)
    Handler.router = Router(task_service, analysis_service)
    Handler.settings = settings
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    server.daemon_threads = True
    return server


def main() -> None:
    settings = load_settings()
    server = build_server(settings)
    info("server_started", host=settings.host, port=settings.port, env=settings.app_env)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        info("server_stopping")
    finally:
        server.server_close()
        info("server_stopped")


if __name__ == "__main__":
    main()
