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
import time
import pathlib
import threading
import urllib.request
import urllib.error
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

APP_ID = os.environ.get("LARK_APP_ID") or ""
APP_SECRET = os.environ.get("LARK_APP_SECRET") or ""
if not APP_ID or not APP_SECRET:
    raise RuntimeError("LARK_APP_ID / LARK_APP_SECRET 未设置，请配置 ~/.nsksd-content/config.json 或 export 环境变量")

TRIGGERS_DIR = SCRIPT_DIR / "triggers"
TRIGGERS_DIR.mkdir(exist_ok=True)
GUIDED_TRIGGERS_DIR = TRIGGERS_DIR / "guided"
GUIDED_TRIGGERS_DIR.mkdir(exist_ok=True)

# tenant_access_token 缓存(2 小时 TTL)
_TOKEN_CACHE = {"token": None, "expires_at": 0}


def get_tenant_token() -> str:
    """飞书 tenant_access_token,2h TTL 缓存"""
    if _TOKEN_CACHE["token"] and time.time() < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"获取 tenant_token 失败: {data}")
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = time.time() + 7000  # 比 7200 留点余量
    return token


def send_follow_up_card(open_chat_id: str, card: dict) -> dict:
    """异步发新卡片到同一会话(用于通知类卡片,不占用 callback return)"""
    try:
        token = get_tenant_token()
        payload = {
            "receive_id": open_chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        log(f"[follow-up] send_result code={result.get('code')} msg_id={result.get('data',{}).get('message_id')}")
        return result
    except Exception as e:
        log(f"[follow-up 失败] {e}")
        return {"error": str(e)}


def build_writing_notify_card(chosen_titles: list) -> dict:
    """⏳ 正在撰写中 通知卡(yellow header, 无交互)"""
    titles_md = "\n".join(f"• {t}" for t in chosen_titles) or "(无)"
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": "yellow",
            "title": {"tag": "plain_text",
                      "content": f"⏳ 已接单 · 正在撰写 {len(chosen_titles)} 篇"},
            "subtitle": {"tag": "plain_text",
                         "content": "Claude Code 流水线启动,预计 5-8 分钟/篇"},
        },
        "body": {
            "elements": [
                {"tag": "markdown",
                 "content": f"**本次撰写任务**\n\n{titles_md}"},
                {"tag": "hr"},
                {"tag": "markdown",
                 "content": "**流水线 5 步**\n\n"
                            "1️⃣ title-outliner · 标题与大纲\n"
                            "2️⃣ article-writer · 正文(nsksd-writing-style)\n"
                            "3️⃣ quyu-view-checker · 禁用词扫描\n"
                            "4️⃣ image-designer · Bento Grid 配图\n"
                            "5️⃣ format-publisher · 推送公众号草稿箱\n\n"
                            "✅ 完成后会推「已推送草稿箱」卡片"},
            ]
        },
    }


def write_trigger_file(session_id: str, chosen_titles: list, chosen_ids: list,
                        open_chat_id: str):
    """写 trigger 文件,主 Agent 轮询此目录就能接单跑流水线"""
    trigger_path = TRIGGERS_DIR / f"{session_id}.trigger"
    payload = {
        "session_id": session_id,
        "chosen_ids": chosen_ids,
        "chosen_titles": chosen_titles,
        "open_chat_id": open_chat_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "pending",
    }
    trigger_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    log(f"[trigger] 写入 {trigger_path.name}")


def log(msg: str):
    stamped = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(stamped, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(stamped + "\n")


def write_session_reply(session_id: str, step: str, feedback: str,
                         form_value: dict, button_value: dict, raw_event: dict):
    """把用户回复写入会话 JSON,主 Agent 轮询此文件可拿到结果

    form_value 里包含所有表单字段(choices 多选 / user_feedback 文本 等),整体落盘
    """
    path = SESSIONS_DIR / f"{session_id}.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    # 多选字段:支持 choices(multi_select) 或 checker_* 系列(checker 平铺)
    choices = form_value.get("choices", [])
    if not choices:
        # checker 模式:收集所有 name 以 opt_ 开头且值为 True 的字段
        choices = [k.replace("opt_", "") for k, v in form_value.items()
                   if k.startswith("opt_") and v is True]
    data.setdefault("replies", []).append({
        "step": step,
        "feedback": feedback,
        "choices": choices,
        "form_value": form_value,
        "button_value": button_value,
        "received_at": datetime.now().isoformat(timespec="seconds"),
    })
    data["latest_step"] = step
    data["latest_feedback"] = feedback
    data["latest_choices"] = choices
    data["latest_form_value"] = form_value
    data["latest_button_value"] = button_value
    data["status"] = "confirmed"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[session 写入] {path.name} step={step} choices={choices}")


def build_locked_choice_card(options: list, form_value: dict,
                              original_title: str = "") -> dict:
    """multi_choice_checker_card 的锁定版

    Args:
        options: 原始选项列表 [{value, text}, ...] 按原序传入,保证渲染顺序稳定
        form_value: 飞书回传的表单值 {opt_{value}: bool, ...}
        original_title: 原卡片 header title,保持一致只加"已锁定"后缀
    """
    # 按原 options 顺序渲染,每个 checker 保留原 text,前面加 ✅/⬜ 标记
    checker_elements = []
    chosen_titles = []
    for opt in options:
        opt_key = f"opt_{opt['value']}"
        picked = bool(form_value.get(opt_key, False))
        mark = "✅" if picked else "⬜"
        checker_elements.append({
            "tag": "checker",
            "text": {"tag": "lark_md",
                     "content": f"{mark}  {opt['text']}"},
            "checked": picked,
            "disabled": True,
        })
        if picked:
            chosen_titles.append(opt["text"])

    chosen_md = "\n".join(f"• {t}" for t in chosen_titles) if chosen_titles \
        else "(未勾选任何选项)"
    header_title = f"{original_title} · 已锁定" if original_title \
        else "日生研NSKSD · 选题多选 · 已锁定"
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": "grey",
            "title": {"tag": "plain_text", "content": header_title},
            "subtitle": {"tag": "plain_text",
                         "content": f"已提交 {len(chosen_titles)} 个选题 · 不可再交互"},
        },
        "body": {
            "elements": [
                *checker_elements,
                {"tag": "hr"},
                {"tag": "markdown",
                 "content": f"**✅ 已选择**\n\n{chosen_md}\n\n⏳ Claude Code 已接单,进入撰写流水线"},
                {"tag": "button",
                 "text": {"tag": "plain_text", "content": "✅ 已提交 · 处理中"},
                 "type": "default", "disabled": True, "width": "fill"},
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
    form_value = {}
    event = {}
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
        write_session_reply(session_id, step, feedback, form_value, button_value, d)
    except Exception as e:
        log(f"[解析失败] {e}")

    # 按卡片类型分流锁定卡
    # 引导卡:button_value.action ∈ {approve, reject}
    # 多选卡:form_value 里有 opt_ 开头的 checker 字段
    action_type = button_value.get("action", "")
    is_guided_card = action_type in ("approve", "reject")
    is_choice_card = (not is_guided_card) and any(
        k.startswith("opt_") for k in form_value.keys())

    if is_guided_card:
        # 引导反馈卡:写 feedback 触发文件 + 返回锁定卡
        from card_builder import build_guided_locked_card
        feedback_text = (form_value.get("feedback_text", "") or "").strip()
        step_name = button_value.get("step_name", "unknown")
        step_index = int(button_value.get("step_index", 0) or 0)
        total_steps = int(button_value.get("total_steps", 5) or 5)

        # 写 guided feedback 触发文件供 trigger_watcher 消费
        fb_path = GUIDED_TRIGGERS_DIR / f"{session_id}-{step_name}.feedback"
        fb_payload = {
            "session_id": session_id,
            "step_name": step_name,
            "step_index": step_index,
            "action": action_type,
            "feedback_text": feedback_text,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "pending",
        }
        fb_path.write_text(json.dumps(fb_payload, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        log(f"[guided trigger] 写入 {fb_path.name} action={action_type}")

        # 取 button.value 里的原卡骨架（避免整个 body 超 2KB）
        skeleton = button_value.get("_skeleton", {}) or {
            "title": f"🧭 引导模式 · 第 {step_index}/{total_steps} 步 · {step_name}",
            "subtitle": "审核产出 → 打回修改 或 通过到下一步",
            "step_output_md": "(原产出未透传)",
        }
        locked = build_guided_locked_card(
            skeleton=skeleton,
            action=action_type,
            feedback_text=feedback_text,
            step_name=step_name,
            step_index=step_index,
            total_steps=total_steps,
        )
        toast_msg = ("✅ 已通过,进入下一步"
                     if action_type == "approve"
                     else "🔴 已打回,Agent 将按意见重做")
    elif is_choice_card:
        # 从 button_value 里拿回原 options(发卡时塞进来的,保证原序原文案)
        options = button_value.get("options") or []
        original_title = button_value.get("original_title", "")
        # 如果没传 options(旧卡片兼容),降级用 opt_ id 渲染
        if not options:
            options = [{"value": k.replace("opt_", ""), "text": k.replace("opt_", "")}
                       for k in sorted(form_value.keys()) if k.startswith("opt_")]

        # 计算选中的选题(按原序)
        chosen_ids = []
        chosen_titles = []
        for opt in options:
            if form_value.get(f"opt_{opt['value']}"):
                chosen_ids.append(opt["value"])
                chosen_titles.append(opt["text"])

        locked = build_locked_choice_card(options, form_value, original_title)
        toast_msg = (f"✅ 已收到 {len(chosen_ids)} 个选题,正在撰写"
                     if chosen_ids else "⚠️ 未勾选任何选题")

        # 异步触发:推「⏳ 正在撰写」通知卡 + 写 trigger 文件
        if chosen_ids:
            open_chat_id = (event.get("context", {}) or {}).get("open_chat_id", "")
            write_trigger_file(session_id, chosen_titles, chosen_ids, open_chat_id)
            if open_chat_id:
                notify = build_writing_notify_card(chosen_titles)
                # 异步发,不阻塞 callback return
                threading.Thread(
                    target=send_follow_up_card,
                    args=(open_chat_id, notify),
                    daemon=True,
                ).start()
    else:
        # v4 定版:只处理多选卡,不再支持 feedback 卡
        locked = {
            "schema": "2.0",
            "config": {"update_multi": True},
            "header": {
                "template": "red",
                "title": {"tag": "plain_text", "content": "⚠️ 未识别的卡片类型"},
            },
            "body": {"elements": [{"tag": "markdown",
                                    "content": "v4 起只支持多选卡,请检查卡片模板"}]},
        }
        toast_msg = "⚠️ 未识别卡片类型"

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
