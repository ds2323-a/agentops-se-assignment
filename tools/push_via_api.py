"""当 git HTTPS 推送被网络代理阻断时，通过 GitHub REST API 提交整棵文件树。

依赖：已认证的 gh CLI。用法：python tools/push_via_api.py
"""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path

REPO = "ds2323-a/agentops-se-assignment"
ROOT = Path(__file__).resolve().parents[1]
SKIP = {"data", ".git", "__pycache__", "output"}


def api(method: str, path: str, payload: dict | None = None, raw: bool = False):
    cmd = ["gh", "api", f"repos/{REPO}/{path}", "--method", method]
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            tmp = f.name
        cmd += ["--input", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{method} {path} failed: {r.stderr.strip()}")
    return (r.stdout if raw else json.loads(r.stdout)) if r.stdout.strip() else {}


def collect_files() -> dict[str, bytes]:
    files = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP or part.startswith(".") and part != ".env.example" for part in rel.parts):
            continue
        if p.suffix in {".pyc", ".db", ".db-wal", ".db-shm"}:
            continue
        files[rel.as_posix()] = p.read_bytes()
    return files


def main():
    # 现有 main 分支状态
    try:
        ref = api("GET", "git/ref/heads/main")
        base_commit = ref["object"]["sha"]
        commit = api("GET", f"git/commits/{base_commit}")
        base_tree = commit["tree"]["sha"]
        parents = [base_commit]
        print("existing main commit:", base_commit[:8])
    except RuntimeError:
        # 空仓库：先用 contents API 写入一个引导文件，产生初始提交
        api("PUT", "contents/README.md", {
            "message": "chore: initialize repository",
            "content": base64.b64encode(b"# AgentOps\n\nInitial commit.\n").decode(),
        })
        ref = api("GET", "git/ref/heads/main")
        base_commit = ref["object"]["sha"]
        commit = api("GET", f"git/commits/{base_commit}")
        base_tree = commit["tree"]["sha"]
        parents = [base_commit]
        print("initialized empty repo with commit:", base_commit[:8])

    files = collect_files()
    print("uploading", len(files), "files")

    tree_entries = []
    for path, content in sorted(files.items()):
        blob = api("POST", "git/blobs", {"content": base64.b64encode(content).decode(), "encoding": "base64"})
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("  blob", path)

    tree_payload = {"tree": tree_entries}
    if base_tree:
        tree_payload["base_tree"] = base_tree
    tree = api("POST", "git/trees", tree_payload)

    new_commit = api("POST", "git/commits", {
        "message": "feat: AgentOps 分级规划与失效分析平台（完整课程大作业）",
        "tree": tree["sha"],
        "parents": parents,
    })
    if parents:
        api("PATCH", "git/refs/heads/main", {"sha": new_commit["sha"], "force": False})
    else:
        api("POST", "git/refs", {"ref": "refs/heads/main", "sha": new_commit["sha"]})
    print("\nPushed commit:", new_commit["sha"])
    print("Repo URL: https://github.com/" + REPO)


if __name__ == "__main__":
    main()
