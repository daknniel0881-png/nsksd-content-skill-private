#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_auditor.py · 事实性挑刺扫描硬门控（V10.4.1 放宽修复）

KPI：找幻觉，不是评质量。四类扫描规则：
  A. orphan_number   — 具体数字无任何出处线索（默认 low，只有完全裸奔才 high）
  B. weasel_phrase   — 懒惰话术（研究表明 / 专家认为 / 据统计 …）严格保留
  C. non_whitelist_source — 正文来源括号里的机构/期刊不在白名单内（medium，不阻断）
  D. institution_without_doi — 大学/研究所/医院 + 年份 + 研究，同段无任何合规载体

V10.4.1 修复过度的点：
  · 规则 A：同段含 [数字] 脚注 / 《刊物》/ 研究/试验/发表 等出处线索 → 自动通过
  · 规则 A：真正 high 只留"孤零零数字+单位，段内毫无任何出处语言"
  · 规则 D：合规载体扩展到 `公众号刊文 / 发表于 / 刊文 / [数字]脚注`

输出：
  step3-fact-audit.json（写入同目录）

退出码：
  0 = 通过（无 high severity）
  1 = 发现可疑（≥1 条 high）
  2 = 文件错误

用法：
  python3 scripts/fact_auditor.py artifacts/<SID>/step3-article.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ─────────────────────────────────────────────
# 规则 A: orphan_number —— 数字模式
# ─────────────────────────────────────────────
NUMBER_UNIT_PAT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|mg|μg|ug|IU|FU|kg|g|ml|毫克|毫升|微克|千克|克|mm|cm)"
)
# 强来源标注（命中即通过，且段内无需进一步判断）
SOURCE_STRONG_PAT = re.compile(
    r"[（(]\s*(?:来源|出处|引自|参考)[：:]|"
    r"DOI\s*[:：]|"
    r"https?://|"
    r"《[^》]{1,40}》"
)
# 软出处线索：段内有 [数字]脚注 / 研究/试验/发表/刊文/公众号 等，
# 说明作者其实挂了参考文献或交代了出处来源 —— 宽松通过
SOURCE_SOFT_PAT = re.compile(
    r"\[\d{1,3}\]|"                        # [1] [12] 脚注
    r"[\u4e00-\u9fa5]研究[^，。\n]{0,20}(?:发现|显示|指出|表明)|"
    r"试验|临床|队列|综述|meta\s*分析|"
    r"发表于|刊文|公众号|官方|白皮书|指南|声明"
)
# 机构名 + 年份（规则 A 附加判断：机构出现时年份也要求有 DOI/URL/期刊）
INSTITUTION_PAT = re.compile(
    r"[\u4e00-\u9fa5]{2,8}(?:大学|学院|研究所|医院|研究中心|委员会|学会)"
)

# ─────────────────────────────────────────────
# 规则 B: weasel_phrase
# ─────────────────────────────────────────────
WEASEL_TERMS = [
    "研究表明", "专家认为", "据统计", "有报道称",
    "相关数据显示", "业内人士", "权威人士", "国外研究",
    "临床证明", "大量研究", "科学家发现", "医学界公认",
    "业界普遍认为",
]
WEASEL_PAT = re.compile("|".join(re.escape(t) for t in WEASEL_TERMS))

# ─────────────────────────────────────────────
# 规则 C: non_whitelist_source
# ─────────────────────────────────────────────
SOURCE_BRACKET_PAT = re.compile(
    r"[（(]\s*(?:来源|出处|引自)[：:]\s*([^）)]{1,100})[）)]"
)

# ─────────────────────────────────────────────
# 规则 D: institution_without_doi
# ─────────────────────────────────────────────
INST_YEAR_STUDY_PAT = re.compile(
    r"([\u4e00-\u9fa5]{2,8}(?:大学|学院|研究所|医院|研究中心|委员会|学会))"
    r".{0,30}"
    r"((?:19|20)\d{2})\s*年"
    r".{0,30}"
    r"(?:研究|试验|调查|报告|实验|临床|数据|发现)"
)
DOI_URL_JOURNAL_PAT = re.compile(
    r"DOI\s*[:：]|https?://|《[^》]{1,40}》|\d{4}\s*[，,]\s*\d+|"
    r"\[\d{1,3}\]|发表于|刊文|公众号|官方声明|白皮书|指南"
)


# ─────────────────────────────────────────────
# 白名单解析
# ─────────────────────────────────────────────
def load_whitelist(whitelist_path: Path) -> set[str]:
    """从 whitelist-sources.md 提取所有「源名称」列的条目。文件缺失时 exit(2)。"""
    if not whitelist_path.exists():
        print(f"[fatal] 白名单文件缺失: {whitelist_path}", file=sys.stderr)
        sys.exit(2)
    text = whitelist_path.read_text(encoding="utf-8")
    names: set[str] = set()
    # 表格行：| 源名称 | URL | ... —— 取第一列（去掉 header 行）
    row_pat = re.compile(r"^\|\s*([^|]+?)\s*\|")
    for line in text.splitlines():
        m = row_pat.match(line.strip())
        if not m:
            continue
        cell = m.group(1).strip()
        # 跳过 header / 分隔行
        if cell in ("源名称", "---", "") or set(cell) == {"-"}:
            continue
        # 同一格内可能有括号注释，取主名称
        cell = re.sub(r"[（(（][^)））]*[)））]", "", cell).strip()
        if cell:
            names.add(cell)
    return names


def source_in_whitelist(source_text: str, whitelist: set[str]) -> bool:
    """检查括号内的来源文本是否命中白名单中任一条目（白名单条目是正文来源的子串）。"""
    source_text = source_text.strip()
    for wl in whitelist:
        if len(wl) >= 2 and wl in source_text:
            return True
    # DOI / URL 当作自带来源，自动通过
    if re.search(r"DOI\s*[:：]|https?://", source_text):
        return True
    return False


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def get_line_number(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def ctx(text: str, pos: int, pad: int = 40) -> str:
    s = max(0, pos - pad)
    e = min(len(text), pos + pad)
    return text[s:e].replace("\n", " ").strip()


def get_paragraph(text: str, pos: int) -> str:
    """返回 pos 所在段落（双换行分隔）。"""
    start = text.rfind("\n\n", 0, pos)
    start = start + 2 if start != -1 else 0
    end = text.find("\n\n", pos)
    end = end if end != -1 else len(text)
    return text[start:end]


# ─────────────────────────────────────────────
# 四条扫描规则
# ─────────────────────────────────────────────
def scan_orphan_numbers(text: str) -> list[dict]:
    """V10.4.1 放宽：
      · 段内命中 SOURCE_STRONG_PAT（来源/DOI/URL/《刊物》）→ 不计入（作者已交代出处）
      · 段内命中 SOURCE_SOFT_PAT（[n]脚注/研究/发表/公众号 等）→ 不计入（软出处）
      · 段内完全没有任何出处语言 → 才记为 high
    目的：数字本身不是问题，无法溯源的数字才是问题。
    """
    findings = []
    for m in NUMBER_UNIT_PAT.finditer(text):
        para = get_paragraph(text, m.start())
        if SOURCE_STRONG_PAT.search(para) or SOURCE_SOFT_PAT.search(para):
            continue  # 段内已有出处线索，放行
        findings.append({
            "claim": m.group(0),
            "reason": (
                f"具体数字「{m.group(0)}」所在段落完全没有出处语言"
                "（无来源/DOI/URL/《刊物》/[n]脚注/研究/发表 等）"
            ),
            "severity": "high",
            "line": get_line_number(text, m.start()),
            "context": ctx(text, m.start()),
        })
    return findings


def scan_weasel_phrases(text: str) -> list[dict]:
    findings = []
    for m in WEASEL_PAT.finditer(text):
        findings.append({
            "claim": m.group(0),
            "reason": f"懒惰话术「{m.group(0)}」，无锚点来源，读者无法核实",
            "severity": "high",
            "line": get_line_number(text, m.start()),
            "context": ctx(text, m.start()),
        })
    return findings


def scan_non_whitelist_sources(text: str, whitelist: set[str]) -> list[dict]:
    findings = []
    for m in SOURCE_BRACKET_PAT.finditer(text):
        source_text = m.group(1).strip()
        if not source_in_whitelist(source_text, whitelist):
            findings.append({
                "claim": m.group(0),
                "reason": f"来源「{source_text}」不在白名单内，需核实或改写为占位符",
                "severity": "medium",
                "line": get_line_number(text, m.start()),
                "context": ctx(text, m.start()),
            })
    return findings


def scan_institution_without_doi(text: str) -> list[dict]:
    findings = []
    for m in INST_YEAR_STUDY_PAT.finditer(text):
        para = get_paragraph(text, m.start())
        if not DOI_URL_JOURNAL_PAT.search(para):
            findings.append({
                "claim": m.group(0),
                "reason": (
                    f"机构「{m.group(1)}」+ {m.group(2)}年 + 研究，"
                    "但同段无 DOI / URL / 《刊物名》，无法核实"
                ),
                "severity": "high",
                "line": get_line_number(text, m.start()),
                "context": ctx(text, m.start()),
            })
    return findings


# ─────────────────────────────────────────────
# 主逻辑
# ─────────────────────────────────────────────
def audit(md_path: Path, whitelist_path: Path) -> dict:
    raw = md_path.read_text(encoding="utf-8")
    body = strip_frontmatter(raw)
    whitelist = load_whitelist(whitelist_path)

    orphans = scan_orphan_numbers(body)
    weasels = scan_weasel_phrases(body)
    non_wl  = scan_non_whitelist_sources(body, whitelist)
    inst_no_doi = scan_institution_without_doi(body)

    suspicious = orphans + weasels + non_wl + inst_no_doi
    # 按行号排序
    suspicious.sort(key=lambda x: x["line"])

    high   = sum(1 for s in suspicious if s["severity"] == "high")
    medium = sum(1 for s in suspicious if s["severity"] == "medium")
    low    = sum(1 for s in suspicious if s["severity"] == "low")

    stats = {
        "total_claims": len(suspicious),
        "high": high,
        "medium": medium,
        "low": low,
        "weasel_hits": len(weasels),
        "non_whitelist_hits": len(non_wl),
    }

    return {"suspicious": suspicious, "stats": stats}


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 fact_auditor.py <step3-article.md>", file=sys.stderr)
        return 2

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"[错误] 文件不存在: {md_path}", file=sys.stderr)
        return 2

    # 白名单路径：相对于脚本目录的 ../references/whitelist-sources.md
    script_dir = Path(__file__).parent
    whitelist_path = script_dir.parent / "references" / "whitelist-sources.md"

    result = audit(md_path, whitelist_path)

    # 写 JSON 到同目录
    out_path = md_path.parent / "step3-fact-audit.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stats = result["stats"]
    high_count = stats["high"]

    # 友好 stderr 输出
    if result["suspicious"]:
        print(
            f"\n[fact_auditor] 发现 {stats['total_claims']} 条可疑项"
            f"（high={high_count}, medium={stats['medium']}, low={stats['low']}）",
            file=sys.stderr,
        )
        for item in result["suspicious"]:
            print(
                f"  行 {item['line']:>4d} [{item['severity'].upper():^6}] {item['reason']}",
                file=sys.stderr,
            )
            print(f"           上下文: 「{item['context']}」", file=sys.stderr)
    else:
        print("[fact_auditor] 未发现可疑事实性问题，通过", file=sys.stderr)

    print(f"[fact_auditor] 结果写入: {out_path}", file=sys.stderr)

    if high_count >= 1:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
