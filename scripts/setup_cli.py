#!/usr/bin/env python3
"""
NSKSD Content Skill · 首次安装引导
运行方式: python3 scripts/setup_cli.py

功能：
- 检查 ~/.nsksd-content/config.json 是否存在
- 不存在时，交互式引导填写凭证
- 存在且字段齐全时，显示脱敏状态表
- 写入时设置 chmod 600
"""

import json
import os
import stat
import sys
from pathlib import Path
from typing import Optional

# 将 scripts/ 加入路径，确保 lib.openid_resolver 可导入
sys.path.insert(0, str(Path(__file__).parent))
from lib.openid_resolver import get_self_open_id, list_my_chats

CONFIG_DIR = Path.home() / ".nsksd-content"
CONFIG_PATH = CONFIG_DIR / "config.json"

REQUIRED_FIELDS = {
    "wechat": ["app_id", "app_secret"],
    "lark": ["app_id", "app_secret", "target_open_id", "customer_open_chat_id"],
    "settings": ["preferred_theme"],
    "paths": ["output_dir"],
}

DEFAULTS = {
    "wechat": {
        "app_id": "REPLACE_ME",
        "app_secret": "REPLACE_ME",
        "author": "",
    },
    "lark": {
        "app_id": "REPLACE_ME",
        "app_secret": "REPLACE_ME",
        "target_open_id": "REPLACE_ME",
        "customer_open_chat_id": "REPLACE_ME",
    },
    "settings": {
        "preferred_theme": "mint-fresh",
        "auto_open_browser": False,
    },
    "paths": {
        "output_dir": "/tmp/nsksd-output",
    },
}


def mask(value: str) -> str:
    """脱敏显示：前4位 + **** + 后4位"""
    if not value or value == "REPLACE_ME" or len(value) < 9:
        return f"[未填写] {value}" if value == "REPLACE_ME" else value or "[空]"
    return f"{value[:4]}****{value[-4:]}"


def print_status(config: dict) -> None:
    """打印脱敏状态表"""
    print("\n=== 当前凭证状态 ===\n")

    # 微信
    wechat = config.get("wechat", {})
    print("微信公众号")
    print(f"  app_id      : {mask(wechat.get('app_id', ''))}")
    print(f"  app_secret  : {mask(wechat.get('app_secret', ''))}")
    print(f"  author      : {wechat.get('author', '') or '(空，使用默认作者)'}")

    # 飞书
    lark = config.get("lark", {})
    print("\n飞书")
    print(f"  app_id           : {mask(lark.get('app_id', ''))}")
    print(f"  app_secret       : {mask(lark.get('app_secret', ''))}")
    print(f"  target_open_id   : {mask(lark.get('target_open_id', ''))}")
    print(f"  customer_chat_id : {mask(lark.get('customer_open_chat_id', ''))}")

    # 设置
    settings = config.get("settings", {})
    print("\n设置")
    print(f"  preferred_theme  : {settings.get('preferred_theme', 'mint-fresh')}")

    # 路径
    paths = config.get("paths", {})
    print("\n路径")
    print(f"  output_dir       : {paths.get('output_dir', '/tmp/nsksd-output')}")

    print(f"\n配置文件路径: {CONFIG_PATH}")


def ask(prompt: str, default: str = "") -> str:
    """交互式输入，空值回车跳过"""
    hint = f" [{default}]" if default and default != "REPLACE_ME" else " (留空跳过)"
    try:
        value = input(f"{prompt}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return value if value else default


def check_fields_complete(config: dict) -> list:
    """返回缺失或仍为 REPLACE_ME 的字段列表"""
    missing = []
    for section, fields in REQUIRED_FIELDS.items():
        for field in fields:
            val = config.get(section, {}).get(field, "")
            if not val or val == "REPLACE_ME":
                missing.append(f"{section}.{field}")
    return missing


def run_interactive_setup() -> dict:
    """交互式引导填写凭证"""
    print("\n=== NSKSD Content Skill · 首次安装配置 ===\n")
    print("按回车跳过的字段会标为 REPLACE_ME，之后可以再次运行本脚本补填。\n")

    config = {
        "wechat": {**DEFAULTS["wechat"]},
        "lark": {**DEFAULTS["lark"]},
        "settings": {**DEFAULTS["settings"]},
        "paths": {**DEFAULTS["paths"]},
    }

    print("--- 微信公众号凭证 ---")
    print("📎 获取地址：https://mp.weixin.qq.com/  →  登录  →  开发  →  基本配置  →  开发者ID")
    print("   （app_id = 原始 ID 下面的「开发者 ID」；app_secret 需先「重置」再复制）")
    print("   💡 还需在「IP白名单」添加本机出口 IP，否则调用接口会被拒\n")
    config["wechat"]["app_id"] = ask("微信 app_id", "REPLACE_ME")
    config["wechat"]["app_secret"] = ask("微信 app_secret", "REPLACE_ME")
    config["wechat"]["author"] = ask("文章作者名（可留空，默认显示公众号名称）", "")

    print("\n--- 飞书凭证 ---")
    # 修复 问题 #3：旧地址 https://open.feishu.cn/app 会 404，改为 launcher 直链
    print("📎 一键直达开放平台：https://open.feishu.cn/page/launcher?from=backend_oneclick")
    print("   路径：选择/创建自建应用  →  凭证与基础信息")
    print("   - app_id（cli_xxx 格式）")
    print("   - app_secret")
    print("   open_id 查询：https://open.feishu.cn/api-explorer  →  batch_get_id 按手机号反查")
    print("   chat_id 查询：应用管理 → 权限配置 → 加 im:chat 权限，调 /open-apis/im/v1/chats\n")
    config["lark"]["app_id"] = ask("飞书 app_id（cli_xxx 格式）", "REPLACE_ME")
    config["lark"]["app_secret"] = ask("飞书 app_secret", "REPLACE_ME")

    # 自动查询 target_open_id
    auto_open_id = get_self_open_id()
    if auto_open_id:
        config["lark"]["target_open_id"] = auto_open_id
        print(f"[auto] target_open_id = {auto_open_id}")
    else:
        config["lark"]["target_open_id"] = ask(
            "目标 open_id（接收通知的用户，ou_xxx 格式）\n"
            "   提示：也可运行 `lark-cli contact +get-user --as user` 自动查询",
            "REPLACE_ME",
        )

    # 自动列出群聊，让用户选序号
    chats = list_my_chats()
    if chats:
        print("\n当前所在群聊：")
        for i, chat in enumerate(chats):
            print(f"  [{i}] {chat['name']}  ({chat['chat_id']})")
        hint = f"输入序号 0-{len(chats) - 1}（直接回车跳过）"
        try:
            raw = input(f"选择客户群 {hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raw = ""
        if raw.isdigit() and 0 <= int(raw) < len(chats):
            chosen = chats[int(raw)]
            config["lark"]["customer_open_chat_id"] = chosen["chat_id"]
            print(f"[auto] customer_open_chat_id = {chosen['chat_id']}  ({chosen['name']})")
        else:
            config["lark"]["customer_open_chat_id"] = ask(
                "客户群 chat_id（oc_xxx 格式）", "REPLACE_ME"
            )
    else:
        config["lark"]["customer_open_chat_id"] = ask(
            "客户群 chat_id（oc_xxx 格式）\n"
            "   提示：也可运行 `lark-cli im chats list --as user` 自动查询",
            "REPLACE_ME",
        )

    print("\n--- 基础设置 ---")
    theme = ask("默认排版主题", "mint-fresh")
    config["settings"]["preferred_theme"] = theme if theme else "mint-fresh"

    output_dir = ask("输出目录（存放生成的 HTML/图片）", "/tmp/nsksd-output")
    config["paths"]["output_dir"] = output_dir if output_dir else "/tmp/nsksd-output"

    return config


def save_config(config: dict) -> None:
    """写入配置文件，chmod 600"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 600
    print(f"\n✅ 配置已保存：{CONFIG_PATH} (chmod 600)")


def main() -> None:
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[错误] 配置文件 JSON 格式有误：{CONFIG_PATH}")
            print("请手动修复或删除后重新运行。")
            sys.exit(1)

        missing = check_fields_complete(config)
        print_status(config)

        if missing:
            print(f"\n[注意] 以下字段未填写或仍为 REPLACE_ME：")
            for f in missing:
                print(f"  - {f}")
            print("\n📎 快速查询入口：")
            print("   · 微信 app_id/app_secret: https://mp.weixin.qq.com/  →  开发  →  基本配置")
            print("   · 飞书 app_id/app_secret: https://open.feishu.cn/app  →  凭证与基础信息")
            print("   · 飞书 open_id 反查: https://open.feishu.cn/api-explorer  →  batch_get_id")
            print("\n输入 y 进入交互引导补填，其他键退出。")
            try:
                choice = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                sys.exit(0)

            if choice == "y":
                # 只补填缺失字段
                print("\n（已有的字段直接回车保留原值）\n")
                new_config = run_interactive_setup()
                # 合并：新值不为 REPLACE_ME 才覆盖
                for section in ["wechat", "lark", "settings", "paths"]:
                    for key, val in new_config.get(section, {}).items():
                        if val and val != "REPLACE_ME":
                            config.setdefault(section, {})[key] = val
                save_config(config)
        else:
            print("\n✅ 所有必填凭证已配置完成")
    else:
        print(f"配置文件不存在，开始首次安装引导...\n")
        config = run_interactive_setup()
        save_config(config)

    print("\n下一步：运行 `python3 scripts/nsksd_publish.py --help` 试跑")
    print("或直接触发 /nsksd 开始内容生成流水线。\n")


if __name__ == "__main__":
    main()
