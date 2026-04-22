#!/usr/bin/env python3
"""nsksd-content 统一发布入口（V9.5 · 飞书+公众号双推）

流程（V9.5 重构）：
1. **飞书云文档无条件推送**（永远保底，方便预览/审阅/归档）
2. **公众号追加推送**（凭证齐 → 真推草稿；凭证缺 → 明确告知未推；推送失败 → 告警）
3. 通知卡片同时展示两端状态，不再让人误解"飞书推了=公众号推了"

exit code 语义：
- 0 = 飞书 ✅ + 公众号 ✅
- 3 = 飞书 ✅ + 公众号 ⚠️ 未配置凭证（不算错误，按设计走）
- 4 = 飞书 ✅ + 公众号 ❌ 推送失败（网络/token 过期/余额不足等）
- 2 = 输入文件缺失（致命，飞书都没推）

用法：
    python3 scripts/nsksd_publish.py --dir /path/to/formatted/article \
        --customer-chat-id <open_chat_id from trigger>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许作为脚本直接跑
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.credentials import check_credentials, collect_secrets_for_masking, mask_in_text
from lib.feishu_doc_publish import (
    build_failure_notification,
    build_missing_creds_notification,
    build_success_notification,
    create_fallback_doc,
    notify_dual,
    share_doc_to_customer,
)
from lib.credentials import get_admin_open_id, get_target_open_id, load_config
from lib.wechat_publish_core import (
    WeChatPublishError,
    extract_title_from_html,
    find_cover_image,
    get_access_token,
    push_draft,
    replace_all_images,
    upload_thumb_image,
)


def load_article(article_dir: Path) -> tuple[str, str]:
    """返回 (html, title)"""
    html_path = article_dir / "article.html"
    if not html_path.exists():
        raise FileNotFoundError(f"article.html not found in {article_dir}")
    html = html_path.read_text(encoding="utf-8")
    title = extract_title_from_html(html) or article_dir.name
    return html, title


def load_digest(article_dir: Path) -> str:
    """V10.6.1：读 step3-digest.txt（一句话总结，≤54字）。

    查找顺序：
      1. <article_dir>/step3-digest.txt
      2. <article_dir>/digest.txt
      3. <article_dir>/../step3-digest.txt（artifacts/<SID>/ 同级查找）

    缺失即 fail-closed（push_draft 会再次拒绝），禁止走微信自动截首段。
    """
    candidates = [
        article_dir / "step3-digest.txt",
        article_dir / "digest.txt",
        article_dir.parent / "step3-digest.txt",
    ]
    for path in candidates:
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return content
    raise WeChatPublishError(
        "step3-digest.txt 缺失（V10.6.1 硬约束）：article-writer 必须在落盘时产出"
        "一句话摘要文件（≤54字）。查找路径：" + ", ".join(str(c) for c in candidates)
    )


def publish_to_wechat(article_dir: Path, html: str, title: str, author: str) -> str:
    """主路径——成功返回 media_id，失败抛 WeChatPublishError"""
    digest = load_digest(article_dir)  # V10.6.1：发布前必读，缺失即拦截

    token = get_access_token()
    html, _, failed = replace_all_images(html, article_dir, token)
    if failed > 0:
        # 非致命，继续
        pass

    cover = find_cover_image(article_dir)
    if not cover:
        raise WeChatPublishError("未找到封面图（images/ 下需放一张）")
    thumb_media_id = upload_thumb_image(token, str(cover))
    if not thumb_media_id:
        raise WeChatPublishError("封面上传失败")

    media_id = push_draft(token, title, html, thumb_media_id, author, digest=digest)
    if not media_id:
        raise WeChatPublishError("草稿推送返回为空")
    return media_id


def main() -> int:
    parser = argparse.ArgumentParser(description="nsksd 统一发布入口（公众号+飞书保底）")
    parser.add_argument("--dir", "-d", required=True, help="排版好的文章目录")
    parser.add_argument("--author", "-a", default="", help="作者名（可选）")
    parser.add_argument("--customer-chat-id", default=None,
                        help="客户飞书 open_chat_id（从 trigger 文件读）")
    parser.add_argument("--admin-open-id", default=None,
                        help="曲率 admin_open_id override（可选，默认读 config）")
    args = parser.parse_args()

    article_dir = Path(args.dir).resolve()
    secrets = collect_secrets_for_masking()

    try:
        html, title = load_article(article_dir)
    except FileNotFoundError as e:
        msg = mask_in_text(str(e), secrets)
        print(f"[ERR] {msg}", file=sys.stderr)
        return 2

    # ── V9.5 · 铁律：飞书云文档无条件先推一份（保底+审阅+归档）
    doc_url, doc_token = create_fallback_doc(title, html)
    if doc_url:
        print(f"[OK] 飞书云文档已创建：{doc_url}")
        # V10.2：创建后立刻把权限分给客户群 + 曲率 admin
        # 否则只有 bot 能读，客户打开是 403
        if doc_token:
            cfg = load_config()
            members: list[tuple[str, str]] = []
            customer_chat = args.customer_chat_id or get_target_open_id(cfg)
            if customer_chat and customer_chat.startswith("oc_"):
                members.append(("chatid", customer_chat))
            elif customer_chat and customer_chat.startswith("ou_"):
                members.append(("openid", customer_chat))
            admin_open = args.admin_open_id or get_admin_open_id(cfg)
            if admin_open and admin_open.startswith("ou_"):
                members.append(("openid", admin_open))
            if members:
                share_result = share_doc_to_customer(doc_token, members, perm="edit")
                print(f"[OK] 飞书文档权限分发 granted={len(share_result['granted'])} "
                      f"failed={len(share_result['failed'])}")
                if share_result["failed"]:
                    print(f"[WARN] 失败详情：{share_result['failed']}")
    else:
        print("[WARN] 飞书云文档创建失败（lark-cli 未装或超时），继续尝试公众号")

    # ── 公众号是否追加推送，看凭证
    status = check_credentials()

    if status.should_fallback:
        # 场景 A：没配公众号凭证 → 只有飞书
        notif = build_missing_creds_notification(doc_url)
        send_result = notify_dual(notif, args.customer_chat_id, args.admin_open_id)
        print(f"[INFO] 公众号凭证未配置，仅飞书推送 notify={send_result}")
        return 3

    # 场景 B：凭证齐 → 推公众号草稿箱
    try:
        media_id = publish_to_wechat(article_dir, html, title, args.author)
    except WeChatPublishError as e:
        safe_msg = mask_in_text(str(e), secrets)
        notif = build_failure_notification(safe_msg, doc_url)
        send_result = notify_dual(notif, args.customer_chat_id, args.admin_open_id)
        print(f"[ERR] 公众号推送失败：{safe_msg}（飞书文档已推 {doc_url}）notify={send_result}")
        return 4

    # 场景 C：飞书 + 公众号双成功
    notif = build_success_notification(title, media_id)
    # 把 doc_url 也挂到 notification 上一并展示
    notif.doc_url = doc_url
    send_result = notify_dual(notif, args.customer_chat_id, args.admin_open_id)
    print(f"[OK] 飞书+公众号双推完成 media_id={media_id} doc={doc_url} notify={send_result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
