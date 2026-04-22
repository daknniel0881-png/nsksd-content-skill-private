#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_size_check.py · 图片尺寸 + 文字语言硬门控（V10.1 新增）

作用：对 step4-images/ 目录做尺寸 + 数量 + (可选)OCR 语言校验。

硬规范：
  - cover-wechat.png  必须 900 × 383（公众号头图）
  - cover-xhs.png     若存在，必须 1242 × 1660（小红书/视频封面）
  - figure-*.png      至少 3 张（硬下限），最多 8 张
  - 所有图内文字应以中文为主（OCR 可选，需装 pytesseract）

用法:
  python3 scripts/image_size_check.py artifacts/<SID>/step4-images/
  python3 scripts/image_size_check.py artifacts/<SID>/step4-images/ --ocr
  python3 scripts/image_size_check.py artifacts/<SID>/step4-images/ --json

退出码:
  0 = 通过
  1 = 命中违规
  2 = 文件错误
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[错误] 需要 Pillow: pip install Pillow", file=sys.stderr)
    sys.exit(2)

SPEC = {
    "cover-wechat.png": (900, 383),
    "cover-xhs.png": (1242, 1660),
}

INLINE_MIN = 3
INLINE_MAX = 8


def check_size(path: Path, expected: tuple[int, int]) -> dict:
    try:
        w, h = Image.open(path).size
    except Exception as e:
        return {"ok": False, "why": f"无法打开: {e}"}
    ok = (w, h) == expected
    return {
        "ok": ok,
        "actual": (w, h),
        "expected": expected,
        "why": "" if ok else f"尺寸 {w}x{h} ≠ 要求 {expected[0]}x{expected[1]}",
    }


def check_dir(d: Path, use_ocr: bool = False) -> dict:
    findings = {"covers": {}, "inline": {}, "language": []}
    total_issues = 0

    # 封面检查
    wechat_cover = d / "cover-wechat.png"
    # 向后兼容旧命名 cover.png
    if not wechat_cover.exists():
        legacy = d / "cover.png"
        if legacy.exists():
            findings["covers"]["_warning"] = "发现旧命名 cover.png，请重命名为 cover-wechat.png"
            wechat_cover = legacy

    if wechat_cover.exists():
        r = check_size(wechat_cover, SPEC["cover-wechat.png"])
        findings["covers"]["cover-wechat"] = r
        if not r["ok"]:
            total_issues += 1
    else:
        findings["covers"]["cover-wechat"] = {"ok": False, "why": "公众号封面 cover-wechat.png 缺失"}
        total_issues += 1

    xhs_cover = d / "cover-xhs.png"
    if xhs_cover.exists():
        r = check_size(xhs_cover, SPEC["cover-xhs.png"])
        findings["covers"]["cover-xhs"] = r
        if not r["ok"]:
            total_issues += 1
    else:
        findings["covers"]["cover-xhs"] = {"ok": True, "why": "可选：未提供小红书封面"}

    # 内文图数量
    inline_files = sorted(d.glob("figure-*.png"))
    n = len(inline_files)
    findings["inline"] = {
        "count": n,
        "min_required": INLINE_MIN,
        "max_allowed": INLINE_MAX,
        "ok": INLINE_MIN <= n <= INLINE_MAX,
    }
    if not findings["inline"]["ok"]:
        total_issues += 1

    # 可选：OCR 语言扫描
    if use_ocr:
        try:
            import pytesseract
            for p in [wechat_cover, xhs_cover] + inline_files:
                if not p.exists():
                    continue
                try:
                    text = pytesseract.image_to_string(str(p), lang="chi_sim+eng")
                    chi = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
                    eng = sum(1 for c in text if c.isascii() and c.isalpha())
                    lang_ok = chi >= eng or chi >= 5
                    findings["language"].append({
                        "file": p.name,
                        "chinese_chars": chi,
                        "english_chars": eng,
                        "ok": lang_ok,
                        "why": "" if lang_ok else "图内文字以英文为主或中文过少",
                    })
                    if not lang_ok:
                        total_issues += 1
                except Exception as e:
                    findings["language"].append({"file": p.name, "ok": True, "why": f"OCR 失败跳过: {e}"})
        except ImportError:
            findings["language"].append({"warning": "pytesseract 未安装，跳过 OCR 语言检查"})

    return {
        "pass": total_issues == 0,
        "total_issues": total_issues,
        "findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--ocr", action="store_true", help="启用 OCR 图内语言扫描（需要 pytesseract）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = Path(args.dir)
    if not d.exists() or not d.is_dir():
        print(f"[错误] 目录不存在: {d}", file=sys.stderr)
        return 2

    result = check_dir(d, args.ocr)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "✅ 通过" if result["pass"] else "❌ 失败"
        print(f"\n{status}  {d}")
        print(f"  问题总数: {result['total_issues']}\n")
        for k, v in result["findings"]["covers"].items():
            if isinstance(v, dict) and not v.get("ok", True):
                print(f"  封面 {k}: ❌ {v.get('why')}")
            elif isinstance(v, dict):
                print(f"  封面 {k}: ✅ {v.get('actual', '')}")
        il = result["findings"]["inline"]
        mark = "✅" if il["ok"] else "❌"
        print(f"  内文图: {mark} {il['count']} 张 (要求 {il['min_required']}-{il['max_allowed']})")
        for lg in result["findings"]["language"]:
            if "warning" in lg:
                print(f"  OCR: ⚠️ {lg['warning']}")
            elif not lg.get("ok", True):
                print(f"  OCR {lg['file']}: ❌ {lg.get('why')} (中{lg['chinese_chars']}/英{lg['english_chars']})")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
