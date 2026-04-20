#!/usr/bin/env python3
"""
mode_manager.py · 模式管理(v8.3 新增)

管理 skill 的运行模式(auto | guided),支持:
- 读取当前模式(优先 mode_override,回落 default_mode,默认 auto)
- 写入模式(用户口头切换时调用)
- 重置 override(回到 default_mode)

模式存储在 config.json 里,字段:
  default_mode:   "auto" | "guided"      长期默认
  mode_override:  null | "auto" | "guided"  临时覆盖(单次切换后保留,直到下次切换)

用法:
  python3 mode_manager.py get                  # 输出当前生效模式
  python3 mode_manager.py set --mode guided    # 切换到 guided 并固定
  python3 mode_manager.py reset                # 清除 override,回到 default_mode
  python3 mode_manager.py show                 # 显示 default/override/effective
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = SKILL_DIR / "config.json"
CONFIG_EXAMPLE = SKILL_DIR / "config.json.example"


def _load_config() -> dict:
    """读取 config.json,不存在则从 example 拷贝一份。"""
    if not CONFIG_FILE.exists():
        if CONFIG_EXAMPLE.exists():
            CONFIG_FILE.write_text(CONFIG_EXAMPLE.read_text())
        else:
            return {"default_mode": "auto", "mode_override": None}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        print(f"[MODE] config.json 损坏,使用默认值", file=sys.stderr)
        return {"default_mode": "auto", "mode_override": None}


def _save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def get_effective_mode() -> str:
    """返回当前生效模式: override > default > 'auto'"""
    cfg = _load_config()
    override = cfg.get("mode_override")
    if override in ("auto", "guided"):
        return override
    default = cfg.get("default_mode", "auto")
    return default if default in ("auto", "guided") else "auto"


def set_mode(mode: str, persist_as_default: bool = False) -> str:
    """切换模式。默认只写 override(到下次切换仍有效);persist_as_default=True 时同步写 default。"""
    if mode not in ("auto", "guided"):
        print(f"[MODE] 非法模式: {mode}", file=sys.stderr)
        sys.exit(2)
    cfg = _load_config()
    cfg["mode_override"] = mode
    if persist_as_default:
        cfg["default_mode"] = mode
    _save_config(cfg)
    return mode


def reset_mode() -> str:
    """清除 override,回到 default_mode。"""
    cfg = _load_config()
    cfg["mode_override"] = None
    _save_config(cfg)
    return cfg.get("default_mode", "auto")


def show() -> dict:
    cfg = _load_config()
    return {
        "default_mode": cfg.get("default_mode", "auto"),
        "mode_override": cfg.get("mode_override"),
        "effective_mode": get_effective_mode(),
    }


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("get")

    p_set = sub.add_parser("set")
    p_set.add_argument("--mode", choices=["auto", "guided"], required=True)
    p_set.add_argument("--as-default", action="store_true",
                       help="同时更新 default_mode(默认只更新 override)")

    sub.add_parser("reset")
    sub.add_parser("show")

    args = p.parse_args()

    if args.cmd == "get":
        print(get_effective_mode())
    elif args.cmd == "set":
        m = set_mode(args.mode, persist_as_default=args.as_default)
        print(m)
    elif args.cmd == "reset":
        m = reset_mode()
        print(m)
    elif args.cmd == "show":
        info = show()
        for k, v in info.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
