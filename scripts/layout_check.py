#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NSKSD 文章排版自查脚本（V9.9 新增）

硬规则：
  1. 每篇必须有 3-6 个 `## ` 二级小标题
  2. 任何自然段字数 ≤ 100
  3. 小标题不能是「背景/结论/方法」等目录词

用法：
  python3 scripts/layout_check.py artifacts/<SID>/step3-article.md
  python3 scripts/layout_check.py path/to/article.md --json

退出码：
  0 = 通过
  1 = 命中违规
  2 = 文件错误
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PARA_LIMIT = 100
SUBHEADING_MIN = 3
SUBHEADING_MAX = 6

GENERIC_WORDS = {"背景", "方法", "结论", "介绍", "总结", "概述", "前言", "正文", "综上"}


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def count_chars(line: str) -> int:
    return len(re.sub(r"\s+", "", line))


def check(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    body = strip_frontmatter(raw)

    subheadings = re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE)
    subheading_count = len(subheadings)

    paragraphs = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            continue
        if block.startswith(("-", "*", "1.", "2.", "3.", "|", ">")):
            continue
        paragraphs.append(block)

    overflow = []
    max_chars = 0
    for p in paragraphs:
        chars = count_chars(p)
        max_chars = max(max_chars, chars)
        if chars > PARA_LIMIT:
            overflow.append({"chars": chars, "preview": p[:30] + "..."})

    generic_subs = [h for h in subheadings if h.strip() in GENERIC_WORDS]

    issues = []
    if subheading_count < SUBHEADING_MIN:
        issues.append(f"小标题太少：{subheading_count} 个，要 ≥ {SUBHEADING_MIN} 个")
    if subheading_count > SUBHEADING_MAX:
        issues.append(f"小标题太多：{subheading_count} 个，要 ≤ {SUBHEADING_MAX} 个")
    if overflow:
        issues.append(f"超 {PARA_LIMIT} 字的段落 {len(overflow)} 个")
    if generic_subs:
        issues.append(f"目录式小标题 {len(generic_subs)} 个：{generic_subs}")

    return {
        "subheading_count": subheading_count,
        "subheadings": subheadings,
        "max_paragraph_chars": max_chars,
        "paragraph_overflow_count": len(overflow),
        "overflow_samples": overflow[:5],
        "generic_subheadings": generic_subs,
        "pass": len(issues) == 0,
        "issues": issues,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"[错误] 文件不存在: {p}", file=sys.stderr)
        return 2

    result = check(p)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "✅ 通过" if result["pass"] else "❌ 失败"
        print(f"\n{status}  {p}")
        print(f"  二级小标题: {result['subheading_count']} 个 "
              f"(要求 {SUBHEADING_MIN}-{SUBHEADING_MAX})")
        print(f"  最长段落: {result['max_paragraph_chars']} 字 (要求 ≤ {PARA_LIMIT})")
        print(f"  超长段落数: {result['paragraph_overflow_count']}")
        if result["issues"]:
            print("\n问题清单:")
            for i in result["issues"]:
                print(f"  - {i}")
            if result["overflow_samples"]:
                print("\n超长段落样本:")
                for s in result["overflow_samples"]:
                    print(f"  [{s['chars']}字] {s['preview']}")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
