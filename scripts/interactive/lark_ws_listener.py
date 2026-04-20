"""日生研内容创作 · 飞书长连接卡片回调监听器

用途:打磨模式下,每一步都会推一张带输入框的卡片给员工,员工填完修改意见
提交后,此脚本通过飞书 WebSocket 长连接实时收到事件,把用户输入写入
当前会话 JSON(sessions/{session_id}.json),供主 Agent 轮询或读取。

关键设计:
- schema 2.0 卡片 + form 容器 + form_action_type=submit 按钮 = input 值才能回传
- 回调 return 锁定版卡片:保留原正文 + header 灰化 + 展示用户输入 + 按钮禁用
- 事件会同时落盘到 events.log 和 sessions/{session_id}.json

使用:
    python3 lark_ws_listener.py          # 前台运行
    ./run_listener_mac.sh                # Mac 后台启动
    run_listener_win.bat                 # Windows 启动
"""
import json
import os
import sys
import pathlib
from datetime import datetime

import lark_oapi as lark
from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger,
    P2CardActionTriggerResponse,
)

# ---- 配置 ----
SCRIPT_DIR = pathlib.Path(__file__).parent
SESSIONS_DIR = SCRIPT_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
LOG_FILE = SCRIPT_DIR / "events.log"

APP_ID = os.environ.get("LARK_APP_ID", "cli_a939b5f909f81cc1")
APP_SECRET = os.environ.get("LARK_APP_SECRET", "gabdmk0ZZrYWKa8eOGsCjs3Vfo03vg3M")


def log(msg: str):
    stamped = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(stamped, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(stamped + "\n")


def write_session_reply(session_id: str, step: str, feedback: str,
                         button_value: dict, raw_event: dict):
    """把用户回复写入会话 JSON,主 Agent 轮询此文件可拿到结果"""
    path = SESSIONS_DIR / f"{session_id}.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("replies", []).append({
        "step": step,
        "feedback": feedback,
        "button_value": button_value,
        "received_at": datetime.now().isoformat(timespec="seconds"),
    })
    data["latest_step"] = step
    data["latest_feedback"] = feedback
    data["latest_button_value"] = button_value
    data["status"] = "confirmed"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[session 写入] {path.name} step={step}")


def build_locked_card(original_header: dict, original_body_md: str,
                       feedback: str, disabled_label: str = "✅ 已提交 · Claude Code 处理中") -> dict:
    """锁定版卡片:保留原 header 标题文字 + 原正文 + 灰化 + 展示输入 + 禁用按钮"""
    header_title = "已锁定"
    header_subtitle = "已提交 · 不可再交互"
    if original_header:
        if isinstance(original_header.get("title"), dict):
            header_title = original_header["title"].get("content", header_title)
        if isinstance(original_header.get("subtitle"), dict):
            header_subtitle = original_header["subtitle"].get("content", header_subtitle)

    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": "grey",
            "title": {"tag": "plain_text", "content": f"{header_title} · 已锁定"},
            "subtitle": {"tag": "plain_text", "content": header_subtitle},
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": original_body_md or "(原内容)"},
                {"tag": "hr"},
                {
                    "tag": "markdown",
                    "content": f"**修改意见**(已提交)\n\n> {feedback if feedback else '(未填写)'}",
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": disabled_label},
                    "type": "default",
                    "disabled": True,
                    "width": "default",
                },
            ]
        },
    }


def do_card_action_trigger(data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
    raw = lark.JSON.marshal(data)
    log("=" * 60)
    log("[卡片回调事件]")
    log(raw)

    feedback = ""
    button_value = {}
    session_id = "default"
    step = "unknown"
    original_header = {}
    original_body_md = ""

    try:
        d = json.loads(raw)
        event = d.get("event", {}) or d
        action = event.get("action", {}) or {}
        form_value = action.get("form_value", {}) or {}
        button_value = action.get("value", {}) or {}
        feedback = form_value.get("user_feedback", "") or ""
        session_id = button_value.get("session_id", "default")
        step = button_value.get("step", "unknown")
        # 如果 button value 里带了原卡片内容(用于锁定后显示原文),取出来
        original_header = button_value.get("_original_header", {}) or {}
        original_body_md = button_value.get("_original_body_md", "") or ""

        log(f"[form_value] {json.dumps(form_value, ensure_ascii=False)}")
        log(f"[button value] {json.dumps(button_value, ensure_ascii=False)}")
        log(f"[最终输入] '{feedback}' | session={session_id} | step={step}")

        # 写入会话
        write_session_reply(session_id, step, feedback, button_value, d)
    except Exception as e:
        log(f"[解析失败] {e}")

    locked = build_locked_card(original_header, original_body_md, feedback)
    toast_msg = f"✅ 已收到: {feedback[:30]}" if feedback else "✅ 已提交(空内容)"
    return P2CardActionTriggerResponse({
        "toast": {"type": "success", "content": toast_msg},
        "card": {"type": "raw", "data": locked},
    })


def main():
    log(f"[启动] APP_ID={APP_ID}")
    log(f"[会话目录] {SESSIONS_DIR}")
    log("[模式] WebSocket 长连接 · 等待卡片回调...")

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_card_action_trigger(do_card_action_trigger)
        .build()
    )
    client = lark.ws.Client(
        APP_ID, APP_SECRET,
        event_handler=handler,
        log_level=lark.LogLevel.INFO,
    )
    client.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("[退出] Ctrl+C")
        sys.exit(0)
