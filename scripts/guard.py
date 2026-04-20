#!/usr/bin/env python3
"""
guard.py · 流程硬校验门控

作用:在子 Agent 启动前强制校验上一步 artifact 是否存在且有效。
exit 0 = 允许进入该步;exit 非 0 = 拒绝进入。

用法:
  python3 guard.py new-session --mode auto|guided
  python3 guard.py check --sid <SID> --step N
  python3 guard.py confirm --sid <SID> --step N [--user-reply "..."] [--selected "1,3,5"]
  python3 guard.py status --sid <SID>
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = SKILL_DIR / "scripts" / "interactive" / "sessions"
ARTIFACTS_DIR = SKILL_DIR / "artifacts"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def new_session(mode: str) -> str:
    """创建新会话,返回 session_id"""
    sid = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_file = SESSIONS_DIR / f"{sid}.json"
    data = {
        "session_id": sid,
        "mode": mode,
        "created_at": datetime.now().isoformat(),
        "current_step": 0,
        "steps": {
            "1": {"status": "pending", "artifact": None, "confirmed_at": None},
            "2": {"status": "pending", "artifact": None, "confirmed_at": None},
            "3": {"status": "pending", "artifact": None, "confirmed_at": None},
            "4": {"status": "pending", "artifact": None, "confirmed_at": None},
            "5": {"status": "pending", "artifact": None, "confirmed_at": None},
        },
        "replies": {},
    }
    session_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (ARTIFACTS_DIR / sid).mkdir(parents=True, exist_ok=True)
    print(sid)
    return sid


def _load(sid: str) -> dict:
    f = SESSIONS_DIR / f"{sid}.json"
    if not f.exists():
        print(f"[GUARD] 会话不存在: {sid}", file=sys.stderr)
        sys.exit(2)
    return json.loads(f.read_text())


def _save(sid: str, data: dict):
    f = SESSIONS_DIR / f"{sid}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2))


EXPECTED_ARTIFACT = {
    1: "step1-topics.json",
    2: "step2-titles.json",
    3: "step3-article.md",
    4: "step4-images/meta.json",
    5: "step5-media_id.txt",
}


def check(sid: str, step: int) -> int:
    """校验是否可以进入 step N。step 1 总是允许。"""
    data = _load(sid)
    if step == 1:
        print(f"[GUARD] ✅ step 1 允许进入(首步)")
        return 0

    prev = str(step - 1)
    prev_state = data["steps"].get(prev, {})

    if data["mode"] == "guided":
        if prev_state.get("status") != "confirmed":
            print(
                f"[GUARD] ❌ 第 {prev} 步状态 = {prev_state.get('status')},"
                f"非 confirmed,禁止进入第 {step} 步",
                file=sys.stderr,
            )
            return 1
    else:  # auto mode: 只要求 artifact 存在
        if prev_state.get("status") not in ("confirmed", "artifact_ready"):
            print(
                f"[GUARD] ❌ 第 {prev} 步未产出 artifact,禁止进入第 {step} 步",
                file=sys.stderr,
            )
            return 1

    artifact_path = ARTIFACTS_DIR / sid / EXPECTED_ARTIFACT[step - 1]
    if not artifact_path.exists():
        print(
            f"[GUARD] ❌ 第 {prev} 步 artifact 缺失: {artifact_path}",
            file=sys.stderr,
        )
        return 1

    if artifact_path.stat().st_size == 0:
        print(f"[GUARD] ❌ artifact 为空文件: {artifact_path}", file=sys.stderr)
        return 1

    print(f"[GUARD] ✅ step {step} 允许进入(上一步 artifact OK)")
    return 0


def confirm(sid: str, step: int, user_reply: str = None, selected: str = None) -> int:
    """标记 step N 为 confirmed。"""
    data = _load(sid)
    step_key = str(step)

    artifact_path = ARTIFACTS_DIR / sid / EXPECTED_ARTIFACT[step]
    if not artifact_path.exists():
        print(
            f"[GUARD] ⚠️ 第 {step} 步 artifact 不存在({artifact_path}),但仍接受 confirm",
            file=sys.stderr,
        )

    data["steps"][step_key]["status"] = "confirmed"
    data["steps"][step_key]["artifact"] = str(artifact_path)
    data["steps"][step_key]["confirmed_at"] = datetime.now().isoformat()

    reply = data["replies"].get(step_key, {})
    if user_reply is not None:
        reply["feedback"] = user_reply
    if selected is not None:
        reply["selected"] = [int(x) for x in selected.split(",") if x.strip()]
    if reply:
        data["replies"][step_key] = reply

    data["current_step"] = step
    _save(sid, data)
    print(f"[GUARD] ✅ step {step} 已 confirmed")
    return 0


def mark_artifact_ready(sid: str, step: int) -> int:
    """auto 模式:标记 artifact 就绪(不等用户确认)"""
    data = _load(sid)
    step_key = str(step)
    data["steps"][step_key]["status"] = "artifact_ready"
    data["steps"][step_key]["artifact"] = str(
        ARTIFACTS_DIR / sid / EXPECTED_ARTIFACT[step]
    )
    _save(sid, data)
    print(f"[GUARD] ✅ step {step} artifact ready (auto mode)")
    return 0


def status(sid: str) -> int:
    data = _load(sid)
    print(f"Session: {sid}")
    print(f"Mode:    {data['mode']}")
    print(f"Current: step {data['current_step']}")
    for k, v in data["steps"].items():
        print(f"  step {k}: {v['status']}")
    return 0


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new-session")
    p_new.add_argument("--mode", choices=["auto", "guided"], required=True)

    p_chk = sub.add_parser("check")
    p_chk.add_argument("--sid", required=True)
    p_chk.add_argument("--step", type=int, required=True)

    p_cfm = sub.add_parser("confirm")
    p_cfm.add_argument("--sid", required=True)
    p_cfm.add_argument("--step", type=int, required=True)
    p_cfm.add_argument("--user-reply", default=None)
    p_cfm.add_argument("--selected", default=None)

    p_rdy = sub.add_parser("mark-ready")
    p_rdy.add_argument("--sid", required=True)
    p_rdy.add_argument("--step", type=int, required=True)

    p_st = sub.add_parser("status")
    p_st.add_argument("--sid", required=True)

    args = p.parse_args()

    if args.cmd == "new-session":
        new_session(args.mode)
        sys.exit(0)
    elif args.cmd == "check":
        sys.exit(check(args.sid, args.step))
    elif args.cmd == "confirm":
        sys.exit(confirm(args.sid, args.step, args.user_reply, args.selected))
    elif args.cmd == "mark-ready":
        sys.exit(mark_artifact_ready(args.sid, args.step))
    elif args.cmd == "status":
        sys.exit(status(args.sid))


if __name__ == "__main__":
    main()
