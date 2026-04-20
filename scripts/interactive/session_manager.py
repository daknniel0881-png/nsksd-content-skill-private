"""日生研内容创作 · 会话状态管理器

主 Agent 用这个模块:
- 创建新会话(每次启动 skill 生成一个 session_id)
- 写入每步产出(artifacts)
- 轮询等待用户回复(监听器会把飞书卡片提交写进 sessions/{id}.json)
- 读取用户反馈进入下一步

CLI 用法:
    python3 session_manager.py new                       # 新建会话,打印 session_id
    python3 session_manager.py status <id>               # 查当前状态
    python3 session_manager.py wait <id> <step> [timeout_sec=1800]  # 阻塞等用户回复
    python3 session_manager.py set-artifact <id> <step> '<json>'    # 写产出
"""
import json
import sys
import time
import pathlib
from datetime import datetime

SCRIPT_DIR = pathlib.Path(__file__).parent
SESSIONS_DIR = SCRIPT_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def session_path(sid: str) -> pathlib.Path:
    return SESSIONS_DIR / f"{sid}.json"


def new_session() -> str:
    sid = datetime.now().strftime("%Y%m%d-%H%M%S")
    data = {
        "session_id": sid,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "active",
        "current_step": "topic_select",
        "artifacts": {},
        "replies": [],
    }
    session_path(sid).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return sid


def read_session(sid: str) -> dict:
    p = session_path(sid)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_session(sid: str, data: dict):
    session_path(sid).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def set_artifact(sid: str, step: str, artifact: dict):
    data = read_session(sid)
    data.setdefault("artifacts", {})[step] = artifact
    data["current_step"] = step
    write_session(sid, data)


def wait_for_reply(sid: str, step: str, timeout: int = 1800, poll_interval: int = 2):
    """阻塞直到用户提交卡片回复(监听器会写入 replies 数组)"""
    start = time.time()
    while time.time() - start < timeout:
        data = read_session(sid)
        for r in data.get("replies", []):
            if r.get("step") == step:
                return r
        time.sleep(poll_interval)
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "new":
        print(new_session())
    elif cmd == "status" and len(sys.argv) >= 3:
        print(json.dumps(read_session(sys.argv[2]), ensure_ascii=False, indent=2))
    elif cmd == "wait" and len(sys.argv) >= 4:
        sid, step = sys.argv[2], sys.argv[3]
        timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 1800
        reply = wait_for_reply(sid, step, timeout)
        if reply:
            print(json.dumps(reply, ensure_ascii=False, indent=2))
            sys.exit(0)
        else:
            print("TIMEOUT", file=sys.stderr)
            sys.exit(2)
    elif cmd == "set-artifact" and len(sys.argv) >= 5:
        sid, step, artifact_json = sys.argv[2], sys.argv[3], sys.argv[4]
        set_artifact(sid, step, json.loads(artifact_json))
        print("ok")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
