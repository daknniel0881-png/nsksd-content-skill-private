#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_audit.py · 数据引用硬门控（V10.0 新增）

作用：对文章做"事实引用审查"，在 layout_check 之后第二道门控。

扫描点：
  1. 数字断言（百分比/倍数/FU/人数/年份）必须出现在 sources_checked 或 ≤60字 内有来源标注
  2. 孤证检测：涉及健康功效的核心陈述必须有 ≥2 条 sources_checked
  3. 禁用数据词：捏造风险短语（"据研究""有数据显示""权威报告"无具体出处）
  4. 日本表述红线扫描
  5. 医广绝对化词（治疗/根治/治愈/国家批准疗效）
  6. 单位错误扫描（FU 不能写成 mg/IU）

用法:
  python3 scripts/data_audit.py path/to/article.md
  python3 scripts/data_audit.py artifacts/<SID>/step3-article.md --json

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

# ---- 禁用词库 ----

MED_ABSOLUTE = [
    r"治疗(?!仪|师|方案|领域)",  # "治疗"不能用于功效
    r"治愈", r"根治", r"痊愈", r"药效", r"药物替代",
    r"国家批准疗效", r"国家认证药效", r"国家级药品",
    r"当天见效", r"立即见效", r"一次见效", r"一周根治",
    r"最佳疗效", r"最好效果", r"第一疗效", r"唯一有效",
]

JAPAN_FORBIDDEN = [
    r"日本进口", r"日本原装", r"日式工艺", r"日本匠心", r"日本技术独占",
]

FABRICATION_SIGNALS = [
    # 无出处的权威感话术
    r"(?<!【)据研究(?!】)",
    r"(?<!【)有数据显示(?!】)",
    r"(?<!【)权威报告(?:显示|指出|表明)(?!.{0,30}《)",
    r"(?<!【)相关研究表明(?!.{0,30}《)",
    r"(?<!【)某三甲医院(?!.{0,30}《)",
    r"(?<!【)业内人士(?:透露|表示)",
]

UNIT_MISUSE = [
    # FU 是 Fibrin-degrading Unit 纳豆激酶专用单位，不能写成 mg / IU / g
    (r"\b\d{3,5}\s*(mg|毫克|IU)\b", "纳豆激酶剂量单位必须是 FU，不是 mg/IU"),
    (r"纳豆激酶.{0,20}(mg|毫克|IU)\b", "纳豆激酶剂量单位必须是 FU"),
]

# 数字断言正则：百分比、倍数、具体 FU、人数、年份单独出现
NUMBER_CLAIM = re.compile(
    r"(约?\s*\d+(?:\.\d+)?\s*%)"                    # 35%
    r"|(\d+(?:\.\d+)?\s*倍)"                        # 3 倍
    r"|(\d{3,6}\s*FU)"                             # 8000 FU
    r"|(\d+\s*万\s*人)"                             # 120 万人
    r"|(\d+\s*亿\s*人)"                             # 1.2 亿人
    r"|(P\s*[=<>]\s*0\.\d+)"                       # P=0.024
    r"|(\d+\s*人\s*(?:双盲|临床|RCT|队列))"          # 120 人双盲
)

# 来源标注信号：出现即视为该数字有出处
SOURCE_TAGS = [
    r"来源[：:]",
    r"出处[：:]",
    r"《[^》]{2,30}》",
    r"https?://[^\s)]+",
    r"PMID[:：]\s*\d+",
    r"DOI[:：]\s*10\.\d+",
    r"NMPA|EFSA|FDA|WHO|CDC|NIH|PubMed",
    r"(?:中华医学会|国家卫健委|中国营养学会|社科文献出版社)",
]
SOURCE_RE = re.compile("|".join(SOURCE_TAGS))

HEALTH_CORE_CLAIM = re.compile(
    r"(降低|减少|改善|降解|溶解|抑制|缓解|延缓|防治|提升|逆转)"
    r".{0,30}"
    r"(血栓|粘稠|血脂|血压|动脉|斑块|认知|脑梗|心梗|中风|风险)"
)


def strip_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            fm_raw = text[4:end]
            body = text[end + 5:]
            fm = {}
            for line in fm_raw.splitlines():
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip('"')
            # sources_checked 块特殊解析
            m = re.search(r"sources_checked:\s*\n((?:[ \t]+.+\n?)+)", fm_raw)
            fm["_sources_raw"] = m.group(1) if m else ""
            fm["_sources_count"] = len(re.findall(r"url:\s*[\"']?https?://", fm["_sources_raw"]))
            fm["_cross_valid"] = len(re.findall(r"authority_level:\s*1", fm["_sources_raw"]))
            return fm, body
    return {}, text


def scan(text: str, window: int = 60) -> list[dict]:
    """在全文里找数字断言，检查前后 window 字内是否有来源标注"""
    findings = []
    for m in NUMBER_CLAIM.finditer(text):
        start, end = m.span()
        num = next(g for g in m.groups() if g)
        context = text[max(0, start - window): min(len(text), end + window)]
        has_source = bool(SOURCE_RE.search(context))
        if not has_source:
            findings.append({
                "type": "number_without_source",
                "claim": num.strip(),
                "preview": context.strip().replace("\n", " ")[:100],
            })
    return findings


def scan_forbidden(text: str, patterns: list, label: str) -> list[dict]:
    hits = []
    for p in patterns:
        for m in re.finditer(p, text):
            start = max(0, m.start() - 15)
            end = min(len(text), m.end() + 15)
            hits.append({
                "type": label,
                "match": m.group(0),
                "preview": text[start:end].replace("\n", " "),
            })
    return hits


def scan_unit(text: str) -> list[dict]:
    hits = []
    for pat, why in UNIT_MISUSE:
        for m in re.finditer(pat, text):
            start = max(0, m.start() - 20)
            end = min(len(text), m.end() + 20)
            hits.append({
                "type": "unit_misuse",
                "match": m.group(0),
                "why": why,
                "preview": text[start:end].replace("\n", " "),
            })
    return hits


def scan_isolated_claim(body: str, fm: dict) -> list[dict]:
    """健康功效核心陈述必须对应 ≥2 条 sources_checked 且至少 1 条 authority_level:1"""
    claims = list(HEALTH_CORE_CLAIM.finditer(body))
    if not claims:
        return []
    src_count = fm.get("_sources_count", 0)
    level1 = fm.get("_cross_valid", 0)
    issues = []
    if src_count < 2:
        issues.append({
            "type": "isolated_health_claim",
            "claim_count": len(claims),
            "sources_checked_count": src_count,
            "why": f"发现 {len(claims)} 条健康功效核心陈述，但 sources_checked 只有 {src_count} 条，少于 2 条孤证红线",
        })
    if level1 < 1:
        issues.append({
            "type": "no_authority_level_1",
            "why": "健康功效陈述必须至少 1 条 authority_level=1（顶级期刊/官方机构/蓝皮书）",
        })
    return issues


def check(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    fm, body = strip_frontmatter(raw)

    findings = {
        "numbers_without_source": scan(body),
        "medical_absolutes": scan_forbidden(body, MED_ABSOLUTE, "med_absolute"),
        "japan_forbidden": scan_forbidden(body, JAPAN_FORBIDDEN, "japan_forbidden"),
        "fabrication_signals": scan_forbidden(body, FABRICATION_SIGNALS, "fabrication"),
        "unit_misuse": scan_unit(body),
        "isolated_claims": scan_isolated_claim(body, fm),
    }

    total_issues = sum(len(v) for v in findings.values())

    return {
        "pass": total_issues == 0,
        "total_issues": total_issues,
        "sources_checked_count": fm.get("_sources_count", 0),
        "authority_level_1_count": fm.get("_cross_valid", 0),
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
        print(f"  sources_checked 条数: {result['sources_checked_count']}")
        print(f"  authority_level=1 条数: {result['authority_level_1_count']}")
        print(f"  问题总数: {result['total_issues']}")
        for cat, items in result["findings"].items():
            if not items:
                continue
            print(f"\n【{cat}】 {len(items)} 条")
            for it in items[:5]:
                if cat == "numbers_without_source":
                    print(f"  - 数字「{it['claim']}」缺来源 | {it['preview']}")
                elif cat == "unit_misuse":
                    print(f"  - 单位错误「{it['match']}」: {it['why']} | {it['preview']}")
                elif cat == "isolated_claims":
                    print(f"  - {it['why']}")
                else:
                    print(f"  - 「{it['match']}」 | {it.get('preview','')}")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
