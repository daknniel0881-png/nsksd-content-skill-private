#!/usr/bin/env python3
"""nsksd-content 统一发布入口（V9.3 新增）

流程：
1. check_credentials → 决定走主路径还是保底
2. 凭证完备：走 wechat_publish_core.publish
   - 成功：推绿卡
   - 失败：创建飞书保底文档 + 推红卡（exp 场景处理）
3. 凭证缺失：直接创建飞书保底文档 + 推红卡（禁止假装成功）

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
)
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


def publish_to_wechat(article_dir: Path, html: str, title: str, author: str) -> str:
    """主路径——成功返回 media_id，失败抛 WeChatPublishError"""
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

    media_id = push_draft(token, title, html, thumb_media_id, author)
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

    status = check_credentials()

    # ── 场景 1：凭证缺失 → 飞书保底 + 红卡（exp 场景硬约束）
    if status.should_fallback:
        doc_url = create_fallback_doc(title, html)
        notif = build_missing_creds_notification(doc_url)
        send_result = notify_dual(notif, args.customer_chat_id, args.admin_open_id)
        print(f"[WARN] 凭证缺失，已走飞书保底 doc_url={doc_url} notify={send_result}")
        # exit 非 0 让调用方（master-orchestrator）知道没推公众号
        return 3

    # ── 场景 2：凭证完备 → 走主路径
    try:
        media_id = publish_to_wechat(article_dir, html, title, args.author)
    except WeChatPublishError as e:
        safe_msg = mask_in_text(str(e), secrets)
        doc_url = create_fallback_doc(title, html)
        notif = build_failure_notification(safe_msg, doc_url)
        send_result = notify_dual(notif, args.customer_chat_id, args.admin_open_id)
        print(f"[ERR] 公众号推送失败：{safe_msg} → 已启用飞书保底 notify={send_result}")
        return 4

    # ── 成功：绿卡
    notif = build_success_notification(title, media_id)
    send_result = notify_dual(notif, args.customer_chat_id, args.admin_open_id)
    print(f"[OK] 草稿推送成功 media_id={media_id} notify={send_result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
