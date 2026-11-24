"""API 集成测试：启动真实服务，验证关键端点（含错误路径）。"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.server import build_server  # noqa: E402


def request(port, path, method="GET", body=None, expect=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status, payload = resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        status, payload = e.code, json.loads(e.read() or b"null")
    if expect is not None:
        assert status == expect, (path, status, payload)
    return status, payload


def main():
    tmpdir = tempfile.mkdtemp(prefix="agentops-test-")
    port = 18787
    settings = Settings(host="127.0.0.1", port=port,
                        db_path=os.path.join(tmpdir, "test.db"),
                        log_level="ERROR", app_env="testing",
                        cors_origins=("http://127.0.0.1:18787",), request_timeout_s=10)
    server = build_server(settings)
    t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
    time.sleep(0.4)
    checks = []
    try:
        _, o = request(port, "/api/analysis/overview", expect=200)
        checks.append(("GET /api/analysis/overview", o["total_tasks"] == 10))

        _, p = request(port, "/api/analysis/pareto", expect=200)
        checks.append(("GET /api/analysis/pareto", len(p["items"]) > 0 and p["total"] > 0))

        _, c = request(port, "/api/planning/classify", "POST",
                       {"title": "风控策略决策", "description": "支付签名"}, expect=200)
        checks.append(("POST /api/planning/classify", c["level"] == "L3"))

        _, created = request(port, "/api/tasks", "POST",
                             {"title": "批量导出报表数据", "owner": "tester"}, expect=201)
        checks.append(("POST /api/tasks", created["level"] == "L1"))

        _, plan = request(port, f"/api/tasks/{created['id']}/plan", expect=200)
        checks.append(("GET plan", len(plan["steps"]) == 3))

        _, _ = request(port, "/api/tasks", "POST", {"title": "X"}, expect=400)
        checks.append(("validation 400", True))

        _, _ = request(port, "/api/tasks/99999", expect=404)
        checks.append(("not found 404", True))

        _, _ = request(port, "/api/auth/login", "POST",
                       {"username": "admin", "password": "wrong"}, expect=401)
        checks.append(("unauthorized 401", True))

        _, _ = request(port, f"/api/tasks/{created['id']}/runs", "POST",
                       {"agent_name": "Coder-Agent", "outcome": "escalated"}, expect=201)
        _, blocked = request(port, f"/api/tasks/{created['id']}", expect=200)
        checks.append(("run escalated → blocked", blocked["status"] == "blocked"))

        for name, ok in checks:
            print(("PASS " if ok else "FAIL ") + name)
        assert all(ok for _, ok in checks)
        print(f"\n{len(checks)}/{len(checks)} API checks passed")
    finally:
        server.shutdown(); server.server_close()


if __name__ == "__main__":
    main()
