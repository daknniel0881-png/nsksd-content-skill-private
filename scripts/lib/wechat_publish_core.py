#!/usr/bin/env python3
"""微信公众号草稿箱发布核心库（从 signal-ai/publish.py 抽取）

剥离了曲率个人工具链绑定：
- 去掉默认 author（改为调用方显式传）
- 去掉 dotenv 自动加载 signal-ai 的 .env
- 去掉 lark-cli 硬编码通知（通知由 feishu_doc_publish 统一负责）
- 凭证读取走 credentials.py，不读 signal-ai 的 config.json

只保留可复用的 API 封装：
- get_access_token
- upload_thumb_image
- upload_content_image
- download_external_image
- replace_all_images
- push_draft
"""

from __future__ import annotations

import html as html_module
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import requests

from .credentials import check_credentials, load_config, mask

WECHAT_API = "https://api.weixin.qq.com"


class WeChatPublishError(Exception):
    """发布流程异常——message 必须已脱敏"""
    def __init__(self, message: str, errcode: int = 0):
        super().__init__(message)
        self.errcode = errcode


def _resolve_wechat_creds() -> Tuple[str, str]:
    cfg = load_config()
    app_id = os.getenv("WECHAT_APP_ID") or cfg.get("wechat", {}).get("app_id", "")
    app_secret = os.getenv("WECHAT_APP_SECRET") or cfg.get("wechat", {}).get("app_secret", "")
    return app_id, app_secret


def get_current_ip() -> str:
    try:
        resp = requests.get("https://httpbin.org/ip", timeout=10)
        return resp.json().get("origin", "未知")
    except Exception:
        return "未知"


def get_access_token() -> str:
    """获取 access_token。缺凭证或 API 失败均抛 WeChatPublishError（错误消息已脱敏）"""
    status = check_credentials()
    if not status.wechat_ready:
        raise WeChatPublishError(
            f"微信凭证未配置 (missing={status.missing})", errcode=-1
        )
    app_id, app_secret = _resolve_wechat_creds()

    url = f"{WECHAT_API}/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    resp = requests.get(url, timeout=15)
    data = resp.json()
    if "access_token" in data:
        return data["access_token"]

    errcode = data.get("errcode", -1)
    errmsg = data.get("errmsg", "unknown")
    # 脱敏——errmsg 里若回显了 appid/secret 要替换
    safe_msg = errmsg.replace(app_id, mask(app_id)).replace(app_secret, mask(app_secret))
    raise WeChatPublishError(
        f"access_token 获取失败 (errcode={errcode}, errmsg={safe_msg}, appid={mask(app_id)})",
        errcode=errcode,
    )


def upload_thumb_image(token: str, image_path: str) -> Optional[str]:
    url = f"{WECHAT_API}/cgi-bin/material/add_material?access_token={token}&type=image"
    filename = os.path.basename(image_path)
    ext = Path(image_path).suffix.lower()
    ctype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".png": "image/png", ".gif": "image/gif"}.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        files = {"media": (filename, f, ctype)}
        resp = requests.post(url, files=files, timeout=30)
    data = resp.json()
    if "media_id" in data:
        return data["media_id"]
    # 脱敏 token
    safe = json.dumps(data, ensure_ascii=False).replace(token, mask(token))
    raise WeChatPublishError(f"封面上传失败: {safe}")


def upload_content_image(token: str, image_path: str, max_retries: int = 3) -> Optional[str]:
    url = f"{WECHAT_API}/cgi-bin/media/uploadimg?access_token={token}"
    filename = os.path.basename(image_path)
    ext = Path(image_path).suffix.lower()
    ctype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".png": "image/png", ".gif": "image/gif"}.get(ext, "image/jpeg")
    for attempt in range(1, max_retries + 1):
        try:
            with open(image_path, "rb") as f:
                files = {"media": (filename, f, ctype)}
                resp = requests.post(url, files=files, timeout=30)
            data = resp.json()
            if "url" in data:
                return data["url"]
        except Exception:
            pass
        if attempt < max_retries:
            time.sleep(2 * attempt)
    return None


def download_external_image(url: str) -> Optional[str]:
    try:
        url = html_module.unescape(url)
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "png" in ctype:
            ext = ".png"
        elif "gif" in ctype:
            ext = ".gif"
        elif "webp" in ctype:
            ext = ".webp"
        else:
            ext = ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def replace_all_images(html: str, article_dir: Path, token: str) -> Tuple[str, int, int]:
    image_dir = article_dir / "images"
    replaced = 0
    failed = 0

    def _repl(match):
        nonlocal replaced, failed
        src = match.group(1)
        if "mmbiz.qpic.cn" in src:
            return match.group(0)
        if src.startswith(("http://", "https://")):
            local = download_external_image(src)
            if local:
                cdn = upload_content_image(token, local)
                try:
                    os.unlink(local)
                except OSError:
                    pass
                if cdn:
                    replaced += 1
                    return f'src="{cdn}"'
            failed += 1
            return match.group(0)
        local_path = article_dir / src
        if not local_path.exists() and image_dir.exists():
            local_path = image_dir / os.path.basename(src)
        if local_path.exists():
            cdn = upload_content_image(token, str(local_path))
            if cdn:
                replaced += 1
                return f'src="{cdn}"'
        failed += 1
        return match.group(0)

    html = re.sub(r'src="([^"]+)"', _repl, html)
    return html, replaced, failed


def push_draft(token: str, title: str, content: str,
               thumb_media_id: str, author: str = "", digest: str = "") -> Optional[str]:
    url = f"{WECHAT_API}/cgi-bin/draft/add?access_token={token}"
    article = {
        "title": title,
        "author": author,
        "content": content,
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    if digest:
        article["digest"] = digest
    body = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
    resp = requests.post(url, data=body,
                         headers={"Content-Type": "application/json"}, timeout=30)
    result = resp.json()
    if "media_id" in result:
        return result["media_id"]
    errcode = result.get("errcode", -1)
    errmsg = result.get("errmsg", "unknown")
    raise WeChatPublishError(f"草稿推送失败 (errcode={errcode}, errmsg={errmsg})", errcode=errcode)


def extract_title_from_html(html: str) -> Optional[str]:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return None


def find_cover_image(article_dir: Path, cover_arg: Optional[str] = None) -> Optional[Path]:
    if cover_arg:
        p = Path(cover_arg)
        if p.exists():
            return p
        p = article_dir / cover_arg
        if p.exists():
            return p
    image_dir = article_dir / "images"
    if image_dir.exists():
        for pattern in ("cover*.jpg", "cover*.jpeg", "cover*.png", "cover*.gif"):
            covers = sorted(image_dir.glob(pattern))
            if covers:
                return covers[0]
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.gif"):
            covers = sorted(image_dir.glob(ext))
            if covers:
                return covers[0]
    return None
