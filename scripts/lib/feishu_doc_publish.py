#!/usr/bin/env python3
"""飞书云文档保底 + 告警卡片

职责：
1. 把排版好的 HTML/MD 转为飞书云文档，返回 url
2. 推送卡片给客户 open_chat_id + 曲率 admin_open_id
   - 绿卡：公众号推送成功
   - 红卡：凭证缺失 / 推送失败 → 附飞书保底文档 url
3. 所有错误消息过 credentials.mask_in_text 脱敏

依赖：lark-cli（由 Skill setup.sh 装好）
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .credentials import (
    collect_secrets_for_masking,
    get_admin_open_id,
    get_target_open_id,
    load_config,
    mask_in_text,
)


def _lark_cli() -> Optional[str]:
    """自适应 lark-cli 路径：PATH → ~/.local/bin → /opt/homebrew/bin"""
    found = shutil.which("lark-cli")
    if found:
        return found
    for candidate in ("/Users/suze/.local/bin/lark-cli",
                      "/opt/homebrew/bin/lark-cli"):
        if Path(candidate).exists():
            return candidate
    return None


@dataclass
class PublishNotification:
    """一次发布的通知载荷——送给飞书"""
    level: str  # "success" | "warn" | "error"
    title: str
    body: str
    doc_url: Optional[str] = None
    draft_media_id: Optional[str] = None

    def to_card_text(self) -> str:
        """降级版：纯文本卡片（lark-cli 长连接兼容），多行拼接"""
        emoji = {"success": "OK", "warn": "WARN", "error": "ERR"}[self.level]
        lines = [f"[{emoji}] {self.title}", "", self.body]
        if self.doc_url:
            lines += ["", f"飞书保底文档: {self.doc_url}"]
        if self.draft_media_id:
            lines += ["", f"草稿 media_id: {self.draft_media_id}"]
        return "\n".join(lines)


def create_fallback_doc(title: str, html_or_md: str) -> tuple[Optional[str], Optional[str]]:
    """创建飞书云文档作为保底。

    返回 `(doc_url, doc_token)`，失败返回 `(None, None)`。

    V10.2：同时返回 doc_token，方便下一步调 `share_doc_to_customer` 授权。

    坑：`lark-cli docs +create --as bot` 自动把当前 CLI 用户设为 full_access，
    但**其他人读不到**，必须另调 permission.members.create 把客户加协作者。
    """
    cli = _lark_cli()
    if not cli:
        return None, None
    try:
        tmp_dir = tempfile.mkdtemp(prefix="nsksd-fallback-")
        rel_name = "article.md"
        abs_path = Path(tmp_dir) / rel_name
        abs_path.write_text(f"# {title}\n\n{html_or_md}", encoding="utf-8")
        try:
            result = subprocess.run(
                [cli, "docs", "+create",
                 "--title", title,
                 "--markdown", f"@{rel_name}",
                 "--as", "bot"],
                capture_output=True, text=True, timeout=30,
                cwd=tmp_dir,
            )
        finally:
            try:
                abs_path.unlink()
                Path(tmp_dir).rmdir()
            except OSError:
                pass
        if result.returncode != 0:
            return None, None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None, None
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        doc_url = data.get("doc_url") or data.get("url")
        doc_token = data.get("doc_id") or data.get("token")
        return doc_url, doc_token
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None, None


def share_doc_to_customer(doc_token: str,
                          member_ids: list,
                          perm: str = "edit") -> dict:
    """把飞书云文档授权给一组协作者（客户群 / 客户 open_id / 曲率 admin）。

    V10.2 新增：解决"bot 创建的文档只有 bot 能读"。

    Args:
        doc_token: create_fallback_doc 返回的 doc_id
        member_ids: [(member_type, member_id)] 列表
            member_type: "openid" / "chatid" / "userid" / "email" / "unionid"
            chatid = 飞书群（oc_ 开头），群内所有人都能读
            openid = 单个用户（ou_ 开头）
        perm: "view" | "edit" | "full_access"

    Returns:
        {"granted": [...], "failed": [...]}
    """
    cli = _lark_cli()
    if not cli:
        return {"granted": [], "failed": [{"reason": "lark-cli not installed"}]}

    granted, failed = [], []
    params_json = json.dumps({"token": doc_token, "type": "docx"}, ensure_ascii=False)

    for member_type, member_id in member_ids:
        if not member_id or str(member_id).startswith("REPLACE_ME"):
            failed.append({"member_type": member_type, "member_id": member_id,
                           "reason": "member_id 未配置"})
            continue
        data_json = json.dumps({
            "member_type": member_type,
            "member_id": member_id,
            "perm": perm,
        }, ensure_ascii=False)
        try:
            result = subprocess.run(
                [cli, "drive", "permission.members", "create",
                 "--params", params_json,
                 "--data", data_json,
                 "--as", "bot"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                granted.append({"member_type": member_type, "member_id": member_id, "perm": perm})
            else:
                failed.append({"member_type": member_type, "member_id": member_id,
                               "stderr": result.stderr.strip()[:300]})
        except (subprocess.TimeoutExpired, OSError) as e:
            failed.append({"member_type": member_type, "member_id": member_id,
                           "reason": str(e)})
    return {"granted": granted, "failed": failed}


def _send_card(open_id: str, is_chat: bool, text: str) -> bool:
    """通过 lark-cli 发文本卡片。open_chat_id → --chat-id，ou_ → --user-id"""
    cli = _lark_cli()
    if not cli:
        return False
    try:
        cmd = [cli, "im", "+messages-send", "--as", "bot"]
        if is_chat:
            cmd += ["--chat-id", open_id]
        else:
            cmd += ["--user-id", open_id]
        cmd += ["--text", text]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def notify_dual(notif: PublishNotification,
                customer_chat_id: Optional[str] = None,
                admin_open_id_override: Optional[str] = None) -> dict:
    """双发：客户 open_chat_id + 曲率 admin_open_id。返回两端发送结果"""
    cfg = load_config()
    secrets = collect_secrets_for_masking(cfg)
    # 脱敏整个文本
    safe_text = mask_in_text(notif.to_card_text(), secrets)

    target_customer = customer_chat_id or get_target_open_id(cfg)
    target_admin = admin_open_id_override or get_admin_open_id(cfg)

    result = {"customer": False, "admin": False}
    if target_customer:
        result["customer"] = _send_card(target_customer, is_chat=True, text=safe_text)
    if target_admin:
        result["admin"] = _send_card(target_admin, is_chat=False, text=safe_text)
    return result


def build_missing_creds_notification(doc_url: Optional[str]) -> PublishNotification:
    """凭证未配置的红卡——必含落地指引"""
    body = (
        "公众号凭证未配置，已为你生成飞书云文档作为保底阅读入口。\n"
        "如需发布到公众号草稿箱，请执行：\n"
        "  python3 scripts/setup_cli.py init\n"
        "并在 ~/.nsksd-content/config.json 中填入 wechat.app_id / wechat.app_secret"
    )
    return PublishNotification(
        level="error",
        title="公众号凭证未配置 · 已启用飞书保底",
        body=body,
        doc_url=doc_url,
    )


def build_success_notification(title: str, media_id: str) -> PublishNotification:
    return PublishNotification(
        level="success",
        title="公众号草稿推送成功",
        body=f"标题：{title}\n请到 mp.weixin.qq.com → 草稿箱 查看发送。",
        draft_media_id=media_id,
    )


def build_failure_notification(reason: str, doc_url: Optional[str]) -> PublishNotification:
    return PublishNotification(
        level="error",
        title="公众号推送失败 · 已启用飞书保底",
        body=f"原因：{reason}",
        doc_url=doc_url,
    )
