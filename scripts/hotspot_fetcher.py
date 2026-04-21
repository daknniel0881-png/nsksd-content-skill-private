#!/usr/bin/env python3
"""
hotspot_fetcher.py · 健康行业热点抓取器 (v9.3)

调度：每天 09:30 执行（选题生成 10:00 前 30 分钟）
产出：references/topic-library/hotspots/YYYY-MM-DD.json
被谁读：topic-scout 生成 10 选题时强制读取，10 选题中至少 3 个蹭热点

抓取源（三路并行）：
  1. 微信搜索指数（关键词池）— 通过 exa_web_search 兜底
  2. 百度指数榜单（无 key 时抓公开榜单页）
  3. 权威健康媒体 48h 头条（健康界 / 丁香园 / 医学界 / 健康时报）

依赖：
  - requests / httpx（HTTP）
  - BeautifulSoup4（HTML 解析）
  - 可选：exa MCP / web-reader MCP（被 wrapper 脚本注入）

用法：
  python3 scripts/hotspot_fetcher.py
  python3 scripts/hotspot_fetcher.py --date 2026-04-21
  python3 scripts/hotspot_fetcher.py --dry-run        # 不落盘，只打印
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None  # 降级纯打印模式

# ============ 配置 ============

KEYWORDS = [
    "纳豆激酶",
    "心血管疾病",
    "血栓",
    "三高",
    "颈动脉斑块",
    "高血压管理",
    "动脉粥样硬化",
    "卒中预防",
    "血管性认知障碍",
    "溶栓",
]

AUTHORITY_SOURCES = [
    {
        "name": "健康界",
        "url": "https://www.cn-healthcare.com/",
        "selector": "a.title",
        "authority": 2,
    },
    {
        "name": "丁香园",
        "url": "https://www.dxy.cn/",
        "selector": "h3 a",
        "authority": 2,
    },
    {
        "name": "医学界",
        "url": "https://www.yixue.com/",
        "selector": "a.news-title",
        "authority": 2,
    },
    {
        "name": "健康时报",
        "url": "http://www.jksb.com.cn/",
        "selector": "a.news-title",
        "authority": 2,
    },
]

BAIDU_INDEX_RANK_URL = "https://top.baidu.com/board?tab=healthy"

WINDOW_HOURS = 48

# ============ 数据模型 ============

@dataclass
class HotspotItem:
    keyword: str
    title: str
    url: str
    source: str
    authority_level: int  # 1/2/3
    published_at: Optional[str]
    snippet: str
    fetched_at: str
    fetch_method: str  # "exa" / "httpx" / "baidu_rank" / "authority_scrape"


# ============ 抓取器 ============

def fetch_authority_headlines(timeout: float = 10.0) -> list[HotspotItem]:
    """抓四个权威健康媒体的首页头条。"""
    results: list[HotspotItem] = []
    if httpx is None:
        print("[warn] httpx 未安装，跳过 authority 抓取", file=sys.stderr)
        return results

    now_iso = datetime.now(timezone.utc).astimezone().isoformat()
    with httpx.Client(timeout=timeout, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 nsksd-hotspot/9.3"}) as cli:
        for src in AUTHORITY_SOURCES:
            try:
                r = cli.get(src["url"])
                if r.status_code != 200:
                    print(f"[warn] {src['name']} -> HTTP {r.status_code}", file=sys.stderr)
                    continue

                # 轻量解析（避免强依赖 bs4）
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "html.parser")
                    for a in soup.select(src["selector"])[:8]:
                        title = a.get_text(strip=True)
                        href = a.get("href", "")
                        if not title or not href:
                            continue
                        if href.startswith("/"):
                            href = src["url"].rstrip("/") + href

                        # 关键词过滤：只保留命中健康关键词的
                        if not any(kw in title for kw in KEYWORDS + ["健康", "血管", "血压", "血脂"]):
                            continue

                        results.append(HotspotItem(
                            keyword="(authority_headline)",
                            title=title,
                            url=href,
                            source=src["name"],
                            authority_level=src["authority"],
                            published_at=None,
                            snippet=title,
                            fetched_at=now_iso,
                            fetch_method="authority_scrape",
                        ))
                except ImportError:
                    print("[warn] bs4 未安装，authority 抓取降级", file=sys.stderr)
            except Exception as e:
                print(f"[warn] {src['name']} 抓取异常：{e}", file=sys.stderr)

    return results


def fetch_baidu_health_rank(timeout: float = 10.0) -> list[HotspotItem]:
    """抓百度热搜健康榜（无需 API key）。"""
    if httpx is None:
        return []
    now_iso = datetime.now(timezone.utc).astimezone().isoformat()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"}) as cli:
            r = cli.get(BAIDU_INDEX_RANK_URL)
            if r.status_code != 200:
                return []
            # 百度热搜榜前端渲染，尝试从 window.__INITIAL_STATE__ 提取
            # 不成功则返回空（保持健壮）
            import re
            m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', r.text, re.S)
            if not m:
                return []
            try:
                data = json.loads(m.group(1))
                # 结构随百度变化；兼容失败就返回空
                items = data.get("data", {}).get("cards", [{}])[0].get("content", [])
            except Exception:
                return []

            out = []
            for it in items[:15]:
                title = it.get("word", "")
                if not title:
                    continue
                out.append(HotspotItem(
                    keyword="(baidu_rank)",
                    title=title,
                    url=f"https://www.baidu.com/s?wd={title}",
                    source="百度热搜·健康榜",
                    authority_level=2,
                    published_at=None,
                    snippet=it.get("desc", title),
                    fetched_at=now_iso,
                    fetch_method="baidu_rank",
                ))
            return out
    except Exception as e:
        print(f"[warn] baidu rank 异常：{e}", file=sys.stderr)
        return []


def fetch_via_exa_stub(keywords: list[str]) -> list[HotspotItem]:
    """
    通过 exa MCP 搜索微信公众号 + 全网文章。
    这里是 stub —— 由 wrapper 脚本（run_nsksd_daily.sh）
    在外层用 claude -p 调用 MCP 注入真实结果。

    返回空数组时，上层会跳过这路。
    """
    return []


# ============ 主流程 ============

def collect(date_str: str) -> dict:
    items: list[HotspotItem] = []

    print(f"[hotspot] 抓取权威媒体头条...", file=sys.stderr)
    items += fetch_authority_headlines()

    print(f"[hotspot] 抓取百度热搜健康榜...", file=sys.stderr)
    items += fetch_baidu_health_rank()

    print(f"[hotspot] 抓取 exa/微信搜索（stub）...", file=sys.stderr)
    items += fetch_via_exa_stub(KEYWORDS)

    # 去重（按 URL）
    seen = set()
    unique = []
    for it in items:
        if it.url in seen:
            continue
        seen.add(it.url)
        unique.append(it)

    # 排序：一级权威优先，其次按来源
    unique.sort(key=lambda x: (x.authority_level, x.source))

    return {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "window_hours": WINDOW_HOURS,
        "total": len(unique),
        "by_authority": {
            "L1": sum(1 for i in unique if i.authority_level == 1),
            "L2": sum(1 for i in unique if i.authority_level == 2),
            "L3": sum(1 for i in unique if i.authority_level == 3),
        },
        "items": [asdict(i) for i in unique],
        "usage_rules": {
            "min_topics_leveraging_hotspot": 3,
            "must_verify_url_before_citing": True,
            "authority_level_required_for_health_claim": 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skill-root",
                        default=os.environ.get("SKILL_PATH",
                                               str(Path(__file__).resolve().parent.parent)))
    args = parser.parse_args()

    payload = collect(args.date)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    out_dir = Path(args.skill_root) / "references" / "topic-library" / "hotspots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.date}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[hotspot] 落盘 {out_path} · total={payload['total']} L1={payload['by_authority']['L1']} L2={payload['by_authority']['L2']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
