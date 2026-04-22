#!/usr/bin/env python3
"""
openid_resolver.py — 自动查询飞书 open_id / chat_id

通过 lark-cli 命令零参数获取用户 open_id 和群聊列表，
避免 setup 流程中的人工操作。
"""

import json
import subprocess
from typing import Optional


def _run(args: list[str]) -> Optional[dict]:
    """执行 lark-cli 命令，返回解析后的 JSON，失败返回 None。"""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def get_self_open_id() -> Optional[str]:
    """
    查询当前已登录用户的 open_id。

    调用: lark-cli contact +get-user --as user
    成功返回 open_id 字符串（ou_xxx），失败返回 None。
    """
    data = _run(["lark-cli", "contact", "+get-user", "--as", "user"])
    if not data:
        return None
    try:
        return data["data"]["user"]["open_id"] or None
    except (KeyError, TypeError):
        return None


def search_user_open_id(query: str) -> Optional[str]:
    """
    按姓名/手机号/邮箱搜索用户，返回第一条命中的 open_id。

    调用: lark-cli contact +search-user --query "<query>" --as user
    成功返回 open_id 字符串（ou_xxx），失败或无结果返回 None。
    """
    data = _run(["lark-cli", "contact", "+search-user", "--query", query, "--as", "user"])
    if not data:
        return None
    try:
        users = data["data"]["users"]
        if not users:
            return None
        return users[0]["open_id"] or None
    except (KeyError, TypeError, IndexError):
        return None


def list_my_chats() -> list[dict]:
    """
    列出当前用户所在的全部群聊。

    调用: lark-cli im chats list --as user
    返回 [{"name": str, "chat_id": str}, ...]，失败返回空列表。
    """
    data = _run(["lark-cli", "im", "chats", "list", "--as", "user"])
    if not data:
        return []
    try:
        items = data["data"]["items"]
        return [{"name": item["name"], "chat_id": item["chat_id"]} for item in items]
    except (KeyError, TypeError):
        return []


if __name__ == "__main__":
    open_id = get_self_open_id()
    print(f"[self] open_id = {open_id or '(获取失败，请确认 lark-cli 已登录)'}")

    chats = list_my_chats()
    print(f"[chats] {len(chats)} 个群：")
    for i, chat in enumerate(chats):
        print(f"  [{i}] {chat['name']} ({chat['chat_id']})")
