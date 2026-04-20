#!/usr/bin/env python3
"""
topic_history.py · 30 天选题去重日志

三维指纹:
  1. title_hash (标题去停用词后 SHA1 前 12 位)
  2. angle     (核心角度字符串严格匹配)
  3. data_points (数据点集合重合 >= 2 视为重复)

用法:
  python3 topic_history.py load-30d              # 打印 30 天指纹
  python3 topic_history.py check --json '{...}'  # 传入选题 JSON,返回命中与否
  python3 topic_history.py append --json '{...}' # 追加(candidate)
  python3 topic_history.py mark --title-hash XX --status published
  python3 topic_history.py stats                 # 统计
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
HISTORY_FILE = SKILL_DIR / "logs" / "topic-history.jsonl"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

STOP_WORDS = set(
    "的 了 是 在 和 也 吗 啊 吧 就 都 又 还 把 被 让 使 从 向 对 给 由 "
    "这 那 哪 什么 怎么 为什么 如何 多少 几 一 二 三 你 我 他 她 它 "
    "nsksd 纳豆激酶 日生研".split()
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _title_hash(title: str) -> str:
    """去停用词 + SHA1 前 12 位"""
    tokens = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", title.lower())
    kept = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
    key = "|".join(sorted(kept))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def _load_records() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    records = []
    with HISTORY_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def load_fingerprints_30d() -> dict:
    """返回 30 天内的指纹集合"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    titles, angles, data_points_list = {}, {}, []
    for rec in _load_records():
        try:
            dt = datetime.fromisoformat(rec["date"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt < cutoff:
            continue
        th = rec.get("title_hash") or _title_hash(rec.get("title", ""))
        titles[th] = rec["date"]
        if rec.get("angle"):
            angles[rec["angle"]] = rec["date"]
        if rec.get("data_points"):
            data_points_list.append((frozenset(rec["data_points"]), rec["date"]))
    return {
        "titles": titles,
        "angles": angles,
        "data_points": data_points_list,
    }


def check_topic(topic: dict, fingerprints: dict = None) -> dict:
    """检查单个选题是否命中 30 天指纹"""
    if fingerprints is None:
        fingerprints = load_fingerprints_30d()

    title = topic.get("title", "")
    angle = topic.get("angle", "")
    data_points = set(topic.get("data_points", []))

    th = _title_hash(title)
    hits = []

    if th in fingerprints["titles"]:
        hits.append(("title", fingerprints["titles"][th]))

    if angle and angle in fingerprints["angles"]:
        hits.append(("angle", fingerprints["angles"][angle]))

    for dp_set, dp_date in fingerprints["data_points"]:
        overlap = data_points & dp_set
        if len(overlap) >= 2:
            hits.append(("data_points", dp_date, sorted(overlap)))
            break

    return {
        "title_hash": th,
        "hit": bool(hits),
        "hits": hits,
    }


def append_candidate(topic: dict, sid: str = None, used_in: str = "candidate"):
    """追加一条记录"""
    rec = {
        "date": _now_iso(),
        "session_id": sid,
        "title": topic.get("title", ""),
        "title_hash": _title_hash(topic.get("title", "")),
        "line": topic.get("line", ""),
        "angle": topic.get("angle", ""),
        "data_points": list(topic.get("data_points", [])),
        "used_in": used_in,
    }
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def append_candidates(topics: list, sid: str = None):
    for t in topics:
        append_candidate(t, sid=sid, used_in="candidate")


def mark_status(title_hash: str, status: str) -> int:
    """更新指定 title_hash 最新记录的 used_in"""
    records = _load_records()
    updated = 0
    for rec in reversed(records):
        if rec.get("title_hash") == title_hash:
            rec["used_in"] = status
            rec["updated_at"] = _now_iso()
            updated += 1
            break
    if updated:
        with HISTORY_FILE.open("w") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return updated


def stats() -> dict:
    recs = _load_records()
    by_status = {}
    by_line = {}
    cutoff_30 = datetime.now(timezone.utc) - timedelta(days=30)
    recent = 0
    for r in recs:
        by_status[r.get("used_in", "?")] = by_status.get(r.get("used_in", "?"), 0) + 1
        by_line[r.get("line", "?")] = by_line.get(r.get("line", "?"), 0) + 1
        try:
            dt = datetime.fromisoformat(r["date"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff_30:
                recent += 1
        except Exception:
            pass
    return {
        "total": len(recs),
        "recent_30d": recent,
        "by_status": by_status,
        "by_line": by_line,
    }


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("load-30d")
    sub.add_parser("stats")

    p_chk = sub.add_parser("check")
    p_chk.add_argument("--json", required=True)

    p_add = sub.add_parser("append")
    p_add.add_argument("--json", required=True)
    p_add.add_argument("--sid", default=None)
    p_add.add_argument("--status", default="candidate")

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("--title-hash", required=True)
    p_mark.add_argument("--status", required=True)

    args = p.parse_args()

    if args.cmd == "load-30d":
        fp = load_fingerprints_30d()
        print(
            json.dumps(
                {
                    "titles_count": len(fp["titles"]),
                    "angles_count": len(fp["angles"]),
                    "data_points_entries": len(fp["data_points"]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.cmd == "check":
        topic = json.loads(args.json)
        result = check_topic(topic)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1 if result["hit"] else 0)
    elif args.cmd == "append":
        data = json.loads(args.json)
        if isinstance(data, list):
            for t in data:
                append_candidate(t, sid=args.sid, used_in=args.status)
            print(f"appended {len(data)} records")
        else:
            append_candidate(data, sid=args.sid, used_in=args.status)
            print("appended 1 record")
    elif args.cmd == "mark":
        n = mark_status(args.title_hash, args.status)
        print(f"updated {n} records")
    elif args.cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
