#!/usr/bin/env python3
"""日生研 NSKSD · 飞书通知卡推送(供 trigger-watcher / Claude CLI 调用)

用法:
  python3 send_notify.py --chat-id <cid> --kind writing --titles "选题A,选题B"
  python3 send_notify.py --chat-id <cid> --kind done --title "选题A" --draft-url "https://..."
  python3 send_notify.py --chat-id <cid> --kind all_done --count 3
  python3 send_notify.py --chat-id <cid> --kind failed --reason "..."

kind 选项:
  writing  · ⏳ 正在撰写(yellow)
  done     · ✅ 已推送草稿箱(green,单篇)
  all_done · 🎉 全部完成(green,汇总)
  failed   · ❌ 失败(red)
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import pathlib

SCRIPT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from card_builder import notify_card

APP_ID = os.environ.get("LARK_APP_ID") or ""
APP_SECRET = os.environ.get("LARK_APP_SECRET") or ""
if not APP_ID or not APP_SECRET:
    raise RuntimeError("LARK_APP_ID / LARK_APP_SECRET 未设置，请配置 ~/.nsksd-content/config.json 或 export 环境变量")


def get_tenant_token() -> str:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())["tenant_access_token"]


def send(chat_id: str, card: dict) -> dict:
    token = get_tenant_token()
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--kind", required=True,
                    choices=["writing", "done", "all_done", "failed"])
    ap.add_argument("--titles", default="")  # writing 用,逗号分隔
    ap.add_argument("--title", default="")    # done 单篇用
    ap.add_argument("--draft-url", default="")
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    if args.kind == "writing":
        titles = [t.strip() for t in args.titles.split(",") if t.strip()]
        titles_md = "\n".join(f"• {t}" for t in titles) or "(无)"
        card = notify_card(
            title=f"⏳ 已接单 · 正在撰写 {len(titles)} 篇",
            subtitle="Claude Code 流水线启动,预计 5-8 分钟/篇",
            content_md=f"**本次撰写任务**\n\n{titles_md}\n\n---\n\n"
                       f"**流水线 5 步**\n"
                       f"1️⃣ title-outliner · 标题与大纲\n"
                       f"2️⃣ article-writer · 正文(nsksd-writing-style)\n"
                       f"3️⃣ quyu-view-checker · 禁用词扫描\n"
                       f"4️⃣ image-designer · Bento Grid 配图\n"
                       f"5️⃣ format-publisher · 推送公众号草稿箱",
            header_template="yellow",
        )
    elif args.kind == "done":
        card = notify_card(
            title=f"✅ 已推送草稿箱 · {args.title}",
            subtitle="请到微信公众号后台查看",
            content_md=f"**标题**:{args.title}\n\n"
                       f"**草稿链接**:{args.draft_url or '(未提供)'}\n\n"
                       f"下一步:公众号后台检查配图 → 确认推送",
            header_template="green",
        )
    elif args.kind == "all_done":
        card = notify_card(
            title=f"🎉 全部完成 · 共 {args.count} 篇",
            subtitle="所有选题已入草稿箱",
            content_md=f"本次撰写任务已全部完成,共 **{args.count}** 篇推入公众号草稿箱。\n\n"
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

    result = send(args.chat_id, card)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
