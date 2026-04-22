#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
citation_check.py · 引用来源规范硬门控（V10.3 新增）

治的三个病：
  1. 亲昵称谓：正文引用来源写"袁总 / 老袁 / X总 / X哥 / X姐 / X老师"
     → 引用必须用人的原名（如"袁岳"），一次性全名，后续若复用也写全名
  2. 模糊回指：括号里写"来源：同上 / 同前 / 见上 / 同 1"——来源必须每次具名
  3. 来源格式统一：正文里所有括号来源必须走 `（来源：XXX）` 全角括号模板，
     方便 format.py 自动把这段包灰色 span（视觉降级）

扫描点：
  A. 亲昵称谓词库（18 个高频）
  B. 模糊回指（同上/同前/见上/同 N）
  C. 半角括号来源 `(来源: ...)`（必须升级成全角 `（来源：...）`统一样式钩子）

用法：
  python3 scripts/citation_check.py artifacts/<SID>/step3-article.md
  python3 scripts/citation_check.py path/to/article.md --json

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

# ---- A. 亲昵/尊称词库（作为来源标注出现即违规）----
# 规则：姓 + 总/哥/姐/老师/董/爷/叔/姨/教授（未带全名）
# 合法：姓 + 名（两字及以上中文名）/ 机构全称 / 刊物《》
HONORIFIC_SUFFIX = ["总", "哥", "姐", "老师", "董", "爷", "叔", "姨"]
# 允许白名单：完整头衔 + 机构，如 "张文宏教授"（姓+名+教授）合法
# 简化策略：匹配「单姓 + 尊称」 如"袁总 / 老袁 / 小王 / 张姐"
HONORIFIC_PATTERNS = [
    # 单姓 + 尊称后缀（袁总 / 张哥 / 王姐 / 李老师 / 陈董）
    # 括号场景内不要求后边无汉字（"袁总采访"也要被抓），只要求前面不是汉字
    r"(?<![\u4e00-\u9fa5])[\u4e00-\u9fa5](?:" + "|".join(HONORIFIC_SUFFIX) + r")",
    # 老/小 + 单姓（老袁 / 小王）
    r"(?<![\u4e00-\u9fa5])[老小][\u4e00-\u9fa5](?![\u4e00-\u9fa5])",
]

# ---- B. 模糊回指词库 ----
VAGUE_BACKREF = [
    r"来源[：:]\s*同上",
    r"来源[：:]\s*同前",
    r"来源[：:]\s*见上",
    r"来源[：:]\s*如上",
    r"来源[：:]\s*同[1-9一二三四五六七八九十]",
    r"出处[：:]\s*同上",
    r"出处[：:]\s*同前",
    r"出处[：:]\s*见上",
    r"\(\s*同上\s*\)",
    r"（\s*同上\s*）",
]

# ---- C. 半角括号来源（要升级成全角）----
HALF_WIDTH_SOURCE = r"\(\s*(?:来源|出处|引自|参考)[：:]"

# ---- 全角括号来源（合规样式，统计用）----
FULL_WIDTH_SOURCE = r"（\s*(?:来源|出处|引自|参考)[：:][^）]+）"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def _ctx(text: str, m: re.Match, pad: int = 20) -> str:
    s = max(0, m.start() - pad)
    e = min(len(text), m.end() + pad)
    return text[s:e].replace("\n", " ")


def scan_honorifics(text: str) -> list[dict]:
    """只扫「括号来源」或「行首作者位」附近的亲昵称谓，避免误杀正文自然语。

    策略：仅当 honorific 出现在以下任一场景才判违规：
      - 括号来源内：`（来源：袁总 ...）` `(来源：袁总 ...)`
      - 引用图注/作者位：`摘自：袁总 ...` `采访者：袁总` `—— 袁总`
    正文其他地方出现"袁总"不强拦（避免文学化表达误杀）。
    """
    hits = []
    # 场景 1：括号来源内
    source_pattern = re.compile(r"[（(](?:来源|出处|引自|参考|作者|摘自|采访)[：:][^）)]{0,80}[）)]")
    for sm in source_pattern.finditer(text):
        seg = sm.group(0)
        for pat in HONORIFIC_PATTERNS:
            for m in re.finditer(pat, seg):
                hits.append({
                    "type": "honorific_in_source",
                    "match": m.group(0),
                    "preview": seg,
                    "why": "引用来源必须用人物原名（如'袁岳'），禁止亲昵/尊称（袁总/老袁等）",
                })
    # 场景 2：行首作者位 "—— X总" / "摘自：X总"
    authorline = re.compile(
        r"(?:——|采访者|摘自|作者|讲述者|受访者|讲者|演讲人)\s*[：:]?\s*([\u4e00-\u9fa5]{1,3})(?![\u4e00-\u9fa5])"
    )
    for m in authorline.finditer(text):
        name = m.group(1)
        for pat in HONORIFIC_PATTERNS:
            if re.fullmatch(pat, name):
                hits.append({
                    "type": "honorific_in_authorline",
                    "match": name,
                    "preview": _ctx(text, m, 30),
                    "why": "署名/采访人位置必须写原名，禁止亲昵/尊称",
                })
    return hits


def scan_vague_backref(text: str) -> list[dict]:
    hits = []
    for pat in VAGUE_BACKREF:
        for m in re.finditer(pat, text):
            hits.append({
                "type": "vague_backref",
                "match": m.group(0),
                "preview": _ctx(text, m, 30),
                "why": "每次引用必须写清具体来源（人名/机构/《刊物》/URL），禁止'同上/同前/见上'",
            })
    return hits


def scan_half_width_source(text: str) -> list[dict]:
    hits = []
    for m in re.finditer(HALF_WIDTH_SOURCE, text):
        hits.append({
            "type": "half_width_source",
            "match": m.group(0),
            "preview": _ctx(text, m, 30),
            "why": "来源括号必须用全角「（来源：XXX）」（方便排版器自动灰化）",
        })
    return hits


def check(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    body = strip_frontmatter(raw)

    findings = {
        "honorifics": scan_honorifics(body),
        "vague_backref": scan_vague_backref(body),
        "half_width_source": scan_half_width_source(body),
    }

    total = sum(len(v) for v in findings.values())
    full_width_source_count = len(re.findall(FULL_WIDTH_SOURCE, body))

    return {
        "pass": total == 0,
        "total_issues": total,
        "full_width_source_count": full_width_source_count,
        "findings": findings,
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
        print(f"  全角来源标注数: {result['full_width_source_count']}")
        print(f"  问题总数: {result['total_issues']}")
        for cat, items in result["findings"].items():
            if not items:
                continue
            print(f"\n【{cat}】 {len(items)} 条")
            for it in items[:5]:
                print(f"  - 「{it['match']}」: {it['why']}")
                print(f"    上下文: {it['preview']}")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
