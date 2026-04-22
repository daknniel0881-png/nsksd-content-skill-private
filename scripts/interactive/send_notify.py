#!/usr/bin/env python3
"""日生研 NSKSD · 飞书通知卡推送（V9.8 强化 · open_id/chat_id 二选一 + UTF-8 强制）

用法：
  # 单用户 open_id（Windows 测试踩坑 #8 修复）
  python send_notify.py --open-id ou_xxx --kind writing --titles "选题A,选题B"

  # 群 chat_id（老用法保留）
  python send_notify.py --chat-id oc_xxx --kind done --title "选题A" --draft-url "https://..."

  # 不传 --open-id / --chat-id 时，自动从 ~/.nsksd-content/config.json 读
  python send_notify.py --kind all_done --count 3

kind 选项：
  writing  · ⏳ 正在撰写（yellow）
  done     · ✅ 已推送草稿箱（green，单篇）
  all_done · 🎉 全部完成（green，汇总）
  failed   · ❌ 失败（red）

修复（V9.8）：
  - 问题 #8：--chat-id 和 --open-id 二选一，不再硬绑 chat_id
  - 问题 #11：Windows 控制台 stdout 强制 UTF-8，修中文乱码
  - 问题 #4 #5：凭证自动从 ~/.nsksd-content/config.json 加载，零硬编码
"""
import argparse
import io
import json
import os
import pathlib
import sys
import urllib.request

# --- 强制 UTF-8 输出（Windows 控制台 GBK 编码踩坑 #11）---
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from card_builder import notify_card


def _load_config_credentials():
    """优先级：环境变量 > ~/.nsksd-content/config.json"""
    app_id = os.environ.get("LARK_APP_ID") or ""
    app_secret = os.environ.get("LARK_APP_SECRET") or ""
    target_open_id = os.environ.get("TARGET_OPEN_ID") or ""
    target_chat_id = os.environ.get("TARGET_CHAT_ID") or ""

    if app_id and app_secret:
        return app_id, app_secret, target_open_id, target_chat_id

    config_path = pathlib.Path.home() / ".nsksd-content" / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            lark = cfg.get("lark", {}) or {}
            app_id = app_id or lark.get("app_id", "") or ""
            app_secret = app_secret or lark.get("app_secret", "") or ""
            target_open_id = target_open_id or lark.get("target_open_id", "") or ""
            target_chat_id = target_chat_id or lark.get("customer_open_chat_id", "") or ""
        except Exception as e:
            print(f"[警告] 读取 {config_path} 失败: {e}", file=sys.stderr)

    if not app_id or not app_secret:
        raise RuntimeError(
            "LARK_APP_ID / LARK_APP_SECRET 未设置。\n"
            "  方法 1：运行 `python scripts/setup_cli.py` 交互配置\n"
            "  方法 2：export LARK_APP_ID=xxx; export LARK_APP_SECRET=yyy"
        )
    return app_id, app_secret, target_open_id, target_chat_id


APP_ID, APP_SECRET, DEFAULT_OPEN_ID, DEFAULT_CHAT_ID = _load_config_credentials()


def get_tenant_token() -> str:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["tenant_access_token"]


def send(receive_id: str, receive_id_type: str, card: dict) -> dict:
    """receive_id_type: open_id | chat_id | user_id"""
    token = get_tenant_token()
    payload = {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        # ensure_ascii=False + utf-8 encode → 中文不会变 \uXXXX 转义，飞书服务端解码稳定
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    # --chat-id / --open-id 二选一（互斥），兼容旧脚本
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--chat-id", default="", help="群 chat_id（oc_xxx）")
    group.add_argument("--open-id", default="", help="用户 open_id（ou_xxx）")
    ap.add_argument(
        "--kind", required=True, choices=["writing", "done", "all_done", "failed"]
    )
    ap.add_argument("--titles", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--draft-url", default="")
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    # 决定接收者：命令行 > config 默认
    if args.open_id:
        receive_id, receive_id_type = args.open_id, "open_id"
    elif args.chat_id:
        receive_id, receive_id_type = args.chat_id, "chat_id"
    elif DEFAULT_CHAT_ID and DEFAULT_CHAT_ID != "REPLACE_ME":
        receive_id, receive_id_type = DEFAULT_CHAT_ID, "chat_id"
    elif DEFAULT_OPEN_ID and DEFAULT_OPEN_ID != "REPLACE_ME":
        receive_id, receive_id_type = DEFAULT_OPEN_ID, "open_id"
    else:
        raise RuntimeError(
            "未指定 --chat-id 或 --open-id，且 config.json 中 target_open_id/customer_open_chat_id 也未配置"
        )

    if args.kind == "writing":
        titles = [t.strip() for t in args.titles.split(",") if t.strip()]
        titles_md = "\n".join(f"• {t}" for t in titles) or "(无)"
        card = notify_card(
            title=f"⏳ 已接单 · 正在撰写 {len(titles)} 篇",
            subtitle="Claude Code 流水线启动，预计 5-8 分钟/篇",
            content_md=f"**本次撰写任务**\n\n{titles_md}\n\n---\n\n"
            f"**流水线 5 步**\n"
            f"1️⃣ title-outliner · 标题与大纲\n"
            f"2️⃣ article-writer · 正文（nsksd-writing-style）\n"
            f"3️⃣ quyu-view-checker · 禁用词扫描\n"
            f"4️⃣ image-designer · Bento Grid 配图\n"
            f"5️⃣ format-publisher · 推送公众号草稿箱",
            header_template="yellow",
        )
    elif args.kind == "done":
        card = notify_card(
            title=f"✅ 已推送草稿箱 · {args.title}",
            subtitle="请到微信公众号后台查看",
            content_md=f"**标题**：{args.title}\n\n"
            f"**草稿链接**：{args.draft_url or '(未提供)'}\n\n"
            f"下一步：公众号后台检查配图 → 确认推送",
            header_template="green",
        )
    elif args.kind == "all_done":
        card = notify_card(
            title=f"🎉 全部完成 · 共 {args.count} 篇",
            subtitle="所有选题已入草稿箱",
            content_md=f"本次撰写任务已全部完成，共 **{args.count}** 篇推入公众号草稿箱。\n\n"
            f"请到公众号后台逐篇确认 → 群发或定时发布。",
            header_template="green",
        )
    elif args.kind == "failed":
        card = notify_card(
            title="❌ 撰写失败",
            subtitle="需要人工介入",
            content_md=f"**失败原因**\n\n> {args.reason}\n\n"
            f"请查看 logs/writing-*.log 排查。",
            header_template="red",
        )

    result = send(receive_id, receive_id_type, card)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
