#!/usr/bin/env python3
"""凭证加载与脱敏工具

硬约束：
1. 凭证统一从 ~/.nsksd-content/config.json 读取（用户 HOME 目录）
2. 任何对外输出（日志/飞书卡片/异常消息）必须过 mask() 脱敏
3. 缺失凭证时返回 CredentialStatus，由调用方决定保底策略（禁止静默失败）
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path(os.path.expanduser("~/.nsksd-content"))
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class CredentialStatus:
    """凭证状态快照——供调用方判断走主路径还是保底路径"""
    wechat_ready: bool = False
    feishu_ready: bool = False
    missing: list = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def should_fallback(self) -> bool:
        """True 表示必须走飞书保底，不能推公众号"""
        return not self.wechat_ready


def mask(secret: Optional[str], keep: int = 4) -> str:
    """脱敏：前 keep 位 + **** + 后 keep 位

    None / 空串 → "<empty>"
    长度 ≤ 2*keep → 全部 ****（避免泄漏）
    """
    if not secret:
        return "<empty>"
    s = str(secret)
    if len(s) <= keep * 2:
        return "****"
    return f"{s[:keep]}****{s[-keep:]}"


def mask_in_text(text: str, secrets: list) -> str:
    """把 text 里出现的所有 secret 原文替换为脱敏版本，用于日志/卡片正文"""
    out = text or ""
    for sec in secrets:
        if sec and isinstance(sec, str) and len(sec) > 8:
            out = out.replace(sec, mask(sec))
    return out


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 ~/.nsksd-content/config.json，不存在返回空 dict（调用方自行兜底）"""
    target = path or CONFIG_PATH
    if not target.exists():
        return {}
    try:
        with open(target, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def check_credentials(config: Optional[Dict[str, Any]] = None) -> CredentialStatus:
    """检查凭证完整度，返回 CredentialStatus。不抛异常。"""
    cfg = config if config is not None else load_config()
    status = CredentialStatus(raw=cfg)

    # 微信：环境变量优先，fallback 到 config
    wc_app_id = os.getenv("WECHAT_APP_ID") or cfg.get("wechat", {}).get("app_id", "")
    wc_secret = os.getenv("WECHAT_APP_SECRET") or cfg.get("wechat", {}).get("app_secret", "")
    wc_valid = (
        wc_app_id and wc_secret
        and not wc_app_id.startswith("YOUR_")
        and not wc_secret.startswith("YOUR_")
    )
    status.wechat_ready = bool(wc_valid)
    if not wc_valid:
        status.missing.append("wechat.app_id / wechat.app_secret")

    # 飞书：必须全套齐全才算 ready
    fs = cfg.get("feishu", {})
    fs_app_id = os.getenv("FEISHU_APP_ID") or fs.get("app_id", "")
    fs_secret = os.getenv("FEISHU_APP_SECRET") or fs.get("app_secret", "")
    fs_valid = (
        fs_app_id and fs_secret
        and not fs_app_id.startswith("YOUR_")
        and not fs_secret.startswith("YOUR_")
    )
    status.feishu_ready = bool(fs_valid)
    if not fs_valid:
        status.missing.append("feishu.app_id / feishu.app_secret")

    return status


def get_admin_open_id(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """曲率本人的 open_id，用于保底通知"""
    cfg = config if config is not None else load_config()
    return cfg.get("admin_open_id") or cfg.get("feishu", {}).get("admin_open_id")


def get_target_open_id(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """客户侧默认通知对象（trigger 没带 open_chat_id 时的 fallback）"""
    cfg = config if config is not None else load_config()
    return cfg.get("feishu", {}).get("target_open_id")


def collect_secrets_for_masking(config: Optional[Dict[str, Any]] = None) -> list:
    """返回所有需要脱敏的凭证明文串——喂给 mask_in_text"""
    cfg = config if config is not None else load_config()
    secrets = []
    for k in ("app_secret", "app_id"):
        v = cfg.get("wechat", {}).get(k)
        if v and not str(v).startswith("YOUR_"):
            secrets.append(str(v))
        v = cfg.get("feishu", {}).get(k)
        if v and not str(v).startswith("YOUR_"):
            secrets.append(str(v))
    # access_token 是运行时获取的，调用方自己加进来
    for env_key in ("WECHAT_APP_ID", "WECHAT_APP_SECRET", "FEISHU_APP_ID", "FEISHU_APP_SECRET"):
        v = os.getenv(env_key)
        if v:
            secrets.append(v)
    return secrets
