#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redundancy_check.py · 重复词/重复句式软提示扫描（V10.5 T2）

三档检查（全部 warn 级别，exit code 永远 0，不阻断发布）：
  1. high_freq_word   — 2-4 字中文实词出现 ≥ 8 次
  2. repeated_opener  — 段首前 5 字相同模式出现 ≥ 3 次
  3. adjacent_repeat  — 3+ 字中文词在连续两段都出现

stdlib only: re / sys / json / argparse / collections / pathlib

用法：
  python3 scripts/redundancy_check.py <article.md> [--out report.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# ─────────────────────────────────────────────
# Stopwords（最小集，写死）
# ─────────────────────────────────────────────
STOPWORDS: set[str] = {
    "我们", "你们", "他们", "这个", "那个", "这些", "那些",
    "什么", "怎么", "为什么", "但是", "而且", "然后", "所以",
    "因为", "如果", "就是", "还是", "或者", "以及", "一个",
    "一下", "一些", "可以", "可能", "应该", "需要", "已经",
    "正在", "没有", "不是", "的时", "的话", "时候", "问题",
    "方法", "情况",
}

# ─────────────────────────────────────────────
# 正则：提取连续中文 run
# ─────────────────────────────────────────────
ZH_RUN_PAT = re.compile(r"[\u4e00-\u9fa5]+")


def zh_ngrams(text: str, min_n: int = 2, max_n: int = 4) -> list[str]:
    """从文本中每段连续中文 run 提取所有长度在 [min_n, max_n] 的 n-gram 子串。
    例："方法论的核心" → ['方法', '方法论', '方法论的', '法论', '法论的', '论的', '论的核', ...]
    这样 '方法论' 作为一个整体单元被计数，而非被贪婪吞掉。
    """
    result: list[str] = []
    for m in ZH_RUN_PAT.finditer(text):
        run = m.group(0)
        for i in range(len(run)):
            for n in range(min_n, max_n + 1):
                if i + n <= len(run):
                    result.append(run[i:i + n])
    return result


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def get_paragraphs(body: str) -> list[str]:
    """双换行分段，过滤空段。"""
    return [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]


def strip_md_markup(para: str) -> str:
    """去掉 Markdown 标记，保留纯文字。"""
    para = re.sub(r"!\[.*?\]\(.*?\)", "", para)   # 图片
    para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)  # 链接
    para = re.sub(r"`[^`]*`", "", para)            # 行内代码
    para = re.sub(r"[*_~]{1,3}", "", para)         # 粗斜删线
    para = re.sub(r"^#{1,6}\s+", "", para, flags=re.MULTILINE)  # 标题
    para = re.sub(r"^[>\-*+]\s+", "", para, flags=re.MULTILINE)  # 引用/列表
    return para


# ─────────────────────────────────────────────
# 检查项 1：高频实词
# ─────────────────────────────────────────────
FREQ_THRESHOLD = 8
TOP_N = 20


def dedup_ngrams(pairs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """去除碎片 n-gram：若词 A 是词 B 的严格子串，且 B 的频次 ≥ A 频次的 70%，
    则 A 是 B 的碎片，从列表中移除。保留真正有语义的词单元。
    """
    result: list[tuple[str, int]] = []
    words = {w: c for w, c in pairs}
    for word, count in pairs:
        dominated = False
        for other, other_count in pairs:
            if other == word:
                continue
            if word in other and other_count >= count * 0.7:
                dominated = True
                break
        if not dominated:
            result.append((word, count))
    return result


def check_high_freq(paragraphs: list[str]) -> tuple[list[dict], list[tuple[str, int]]]:
    """统计全文 2-4 字中文实词频次，top 20 + warn ≥8 次的词。
    使用滑动 n-gram 确保 '方法论' 等词被完整计数；dedup 去除碎片子串噪音。
    """
    full_text = " ".join(strip_md_markup(p) for p in paragraphs)
    tokens = zh_ngrams(full_text, min_n=2, max_n=4)
    filtered = [t for t in tokens if t not in STOPWORDS]
    counter = Counter(filtered)
    raw_top = counter.most_common(TOP_N * 3)  # 多取一些，dedup 后再截 TOP_N
    deduped = dedup_ngrams(raw_top)[:TOP_N]

    findings: list[dict] = []
    for word, count in deduped:
        if count >= FREQ_THRESHOLD:
            findings.append({
                "check": "high_freq_word",
                "word": word,
                "count": count,
                "severity": "warn",
                "message": f"「{word}」全文出现 {count} 次（阈值 {FREQ_THRESHOLD}），考虑替换同义词",
            })
    return findings, deduped


# ─────────────────────────────────────────────
# 检查项 2：重复段首
# ─────────────────────────────────────────────
OPENER_THRESHOLD = 3


def check_repeated_openers(paragraphs: list[str]) -> list[dict]:
    """取每段开头前 5 个中文字，统计相同段首模式出现 ≥ 3 次。"""
    openers: list[str] = []
    for para in paragraphs:
        clean = strip_md_markup(para)
        zh_chars = re.findall(r"[\u4e00-\u9fa5]", clean)
        key = "".join(zh_chars[:5])
        if key:
            openers.append(key)

    counter = Counter(openers)
    findings: list[dict] = []
    for pattern, count in counter.most_common():
        if count >= OPENER_THRESHOLD:
            findings.append({
                "check": "repeated_opener",
                "pattern": pattern,
                "count": count,
                "severity": "warn",
                "message": (
                    f"段首「{pattern}」出现 {count} 次（阈值 {OPENER_THRESHOLD}），"
                    "句式单一，考虑变换开头方式"
                ),
            })
    return findings


# ─────────────────────────────────────────────
# 检查项 3：近邻重复（连续两段出现同一词）
# ─────────────────────────────────────────────
def check_adjacent_repeats(paragraphs: list[str]) -> list[dict]:
    """同一 3+ 字中文词在连续两段都出现 → warn。"""
    findings: list[dict] = []
    seen_pairs: set[tuple[int, str]] = set()  # 避免同对重复报告

    para_words: list[set[str]] = []
    for para in paragraphs:
        clean = strip_md_markup(para)
        words = set(zh_ngrams(clean, min_n=3, max_n=4))
        words -= STOPWORDS
        para_words.append(words)

    for i in range(len(para_words) - 1):
        overlap = para_words[i] & para_words[i + 1]
        # dedup: drop fragment substrings dominated by a longer word in the same overlap
        overlap_list = sorted(overlap)
        clean_overlap: list[str] = []
        for word in overlap_list:
            dominated = any(
                word in other and other != word and other in overlap
                for other in overlap_list
            )
            if not dominated:
                clean_overlap.append(word)
        for word in clean_overlap:
            key = (i, word)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            findings.append({
                "check": "adjacent_repeat",
                "word": word,
                "para_indices": [i, i + 1],
                "severity": "warn",
                "message": (
                    f"「{word}」在第 {i+1} 段和第 {i+2} 段连续出现，"
                    "考虑在其中一段用代词或省略"
                ),
            })
    return findings


# ─────────────────────────────────────────────
# 人类可读报告
# ─────────────────────────────────────────────
def print_report(
    freq_findings: list[dict],
    opener_findings: list[dict],
    adj_findings: list[dict],
    top20: list[tuple[str, int]],
) -> None:
    total = len(freq_findings) + len(opener_findings) + len(adj_findings)
    print(f"\n{'='*56}")
    print(f"  redundancy_check · 重复词/句式软提示报告")
    print(f"{'='*56}")

    # Top 20 实词频率表
    print(f"\n[TOP 20 实词频次]")
    for i, (word, count) in enumerate(top20, 1):
        flag = " ⚠" if count >= FREQ_THRESHOLD else ""
        print(f"  {i:>2}. {word}  ×{count}{flag}")

    # 高频实词 warn
    print(f"\n[检查 1 · 高频实词] {'发现 ' + str(len(freq_findings)) + ' 条 warn' if freq_findings else '无异常'}")
    for f in freq_findings:
        print(f"  ⚠  {f['message']}")

    # 重复段首 warn
    print(f"\n[检查 2 · 重复段首] {'发现 ' + str(len(opener_findings)) + ' 条 warn' if opener_findings else '无异常'}")
    for f in opener_findings:
        print(f"  ⚠  {f['message']}")

    # 近邻重复 warn
    print(f"\n[检查 3 · 近邻重复] {'发现 ' + str(len(adj_findings)) + ' 条 warn' if adj_findings else '无异常'}")
    for f in adj_findings:
        print(f"  ⚠  {f['message']}")

    print(f"\n{'─'*56}")
    if total == 0:
        print("  全部通过，未发现明显重复问题。")
    else:
        print(f"  合计 {total} 条软提示（warn），供参考，不阻断发布。")
    print(f"{'='*56}\n")


# ─────────────────────────────────────────────
# 主逻辑
# ─────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="redundancy_check · 重复词/重复句式软提示扫描"
    )
    parser.add_argument("article", help="待检查的 Markdown 文件路径")
    parser.add_argument("--out", help="可选：输出 JSON 报告路径", default=None)
    args = parser.parse_args()

    md_path = Path(args.article)
    if not md_path.exists():
        print(f"[错误] 文件不存在: {md_path}", file=sys.stderr)
        return 0  # 软提示，exit 0

    raw = md_path.read_text(encoding="utf-8")
    body = strip_frontmatter(raw)
    paragraphs = get_paragraphs(body)

    if not paragraphs:
        print("[redundancy_check] 文章为空，跳过检查。")
        return 0

    freq_findings, deduped = check_high_freq(paragraphs)
    opener_findings = check_repeated_openers(paragraphs)
    adj_findings = check_adjacent_repeats(paragraphs)

    # stdout 人类可读
    print_report(freq_findings, opener_findings, adj_findings, deduped)

    # 可选 JSON 输出
    if args.out:
        report = {
            "file": str(md_path),
            "stats": {
                "total_warn": len(freq_findings) + len(opener_findings) + len(adj_findings),
                "high_freq_warns": len(freq_findings),
                "repeated_opener_warns": len(opener_findings),
                "adjacent_repeat_warns": len(adj_findings),
            },
            "top20_words": [{"word": w, "count": c} for w, c in deduped],
            "findings": freq_findings + opener_findings + adj_findings,
        }
        out_path = Path(args.out)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[redundancy_check] JSON 报告写入: {out_path}")

    return 0  # 永远 exit 0，软提示不阻断


if __name__ == "__main__":
    sys.exit(main())
