#!/usr/bin/env python3
"""
docs_publisher.py · 云文档 A/B/C 三次预审发布器

- 云文档 A: 第 1 步选题预审(10 个候选)
- 云文档 B: 第 2 步标题大纲预审
- 云文档 C: 第 3+4 步全文 + 配图 + 排版预审

用法:
  python3 docs_publisher.py publish --sid <SID> --step 1|2|5
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = SKILL_DIR / "artifacts"

LARK_BASE = "https://open.feishu.cn/open-apis"


def _env(k: str) -> str:
    v = os.environ.get(k, "")
    if not v:
        sys.stderr.write(f"[docs_publisher] 环境变量 {k} 未设置\n")
        sys.exit(2)
    return v


def _tenant_token() -> str:
    app_id = _env("LARK_APP_ID")
    app_secret = _env("LARK_APP_SECRET")
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        f"{LARK_BASE}/auth/v3/tenant_access_token/internal",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if body.get("code") != 0:
        sys.stderr.write(f"[docs_publisher] 获取 token 失败: {body}\n")
        sys.exit(3)
    return body["tenant_access_token"]


def _create_doc(token: str, title: str) -> str:
    req = urllib.request.Request(
        f"{LARK_BASE}/docx/v1/documents",
        data=json.dumps({"title": title}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if body.get("code") != 0:
        raise RuntimeError(f"创建文档失败: {body}")
    return body["data"]["document"]["document_id"]


def _append_blocks(token: str, doc_id: str, blocks: list):
    """批量追加 block(每批 ≤ 50)"""
    for i in range(0, len(blocks), 50):
        batch = blocks[i : i + 50]
        req = urllib.request.Request(
            f"{LARK_BASE}/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
            data=json.dumps(
                {"children": batch, "index": -1}, ensure_ascii=False
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            body = json.load(resp)
        if body.get("code") != 0:
            sys.stderr.write(f"[docs_publisher] append_blocks 失败: {body}\n")


def _grant(token: str, doc_id: str, open_id: str):
    if not open_id:
        return
    req = urllib.request.Request(
        f"{LARK_BASE}/drive/v1/permissions/{doc_id}/members?type=docx",
        data=json.dumps(
            {"member_type": "openid", "member_id": open_id, "perm": "full_access"}
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req).read()
    except Exception:
        pass


def _text(content: str, bold=False) -> dict:
    elem = {"text_run": {"content": content}}
    if bold:
        elem["text_run"]["text_element_style"] = {"bold": True}
    return elem


def _h2(text: str) -> dict:
    return {"block_type": 4, "heading2": {"elements": [_text(text)]}}


def _h3(text: str) -> dict:
    return {"block_type": 5, "heading3": {"elements": [_text(text)]}}


def _p(text: str, bold=False) -> dict:
    return {"block_type": 2, "text": {"elements": [_text(text, bold=bold)]}}


def _bullet(text: str) -> dict:
    return {"block_type": 16, "bullet": {"elements": [_text(text)]}}


def _divider() -> dict:
    return {"block_type": 22}


def build_doc_a_blocks(sid: str) -> list:
    """云文档 A: 选题预审"""
    step1 = json.load(open(ARTIFACTS_DIR / sid / "step1-topics.json"))
    blocks = [
        _p(f"会话: {sid}  |  生成于: {step1.get('generated_at','')}"),
        _divider(),
    ]
    by_grade = {"S": [], "A": [], "B": []}
    for t in step1["topics"]:
        by_grade.setdefault(t.get("grade", "B"), []).append(t)
    grade_label = {
        "S": "S 级 · 强烈推荐",
        "A": "A 级 · 值得写",
        "B": "B 级 · 备选",
    }
    for g in ("S", "A", "B"):
        if not by_grade.get(g):
            continue
        blocks.append(_h2(grade_label[g]))
        for t in by_grade[g]:
            blocks.append(_h3(f"{t['index']}. {t['title']}"))
            blocks.append(_p(f"内容线: {t.get('line','')} | 评分: {t.get('score','?')} | 合规: {t.get('compliance','🟢')}"))
            blocks.append(_p(f"角度: {t.get('angle','')}"))
            blocks.append(_p(f"目标人群: {t.get('audience','')}"))
            blocks.append(_p(f"钩子: {t.get('hook','')}"))
            if t.get("outline_gist"):
                blocks.append(_p(f"大纲要点: {t['outline_gist']}"))
            if t.get("alt_titles"):
                blocks.append(_p("备选标题:", bold=True))
                for alt in t["alt_titles"]:
                    blocks.append(_bullet(alt))
            blocks.append(_divider())
    return blocks


def build_doc_b_blocks(sid: str) -> list:
    """云文档 B: 标题 + 大纲预审"""
    step2 = json.load(open(ARTIFACTS_DIR / sid / "step2-titles.json"))
    blocks = [_p(f"会话: {sid}"), _divider()]
    for item in step2["items"]:
        blocks.append(_h2(f"选题 {item['topic_index']}: {item['topic_title']}"))
        blocks.append(_p("5 个标题变体:", bold=True))
        for i, t in enumerate(item["titles_variants"], 1):
            rec = " ⭐推荐" if i - 1 == item.get("recommended_title_index") else ""
            blocks.append(_bullet(f"{i}. {t}{rec}"))
        blocks.append(_p("完整大纲:", bold=True))
        outline = item.get("outline", {})
        for key, label in [
            ("hook", "开篇钩子"),
            ("problem", "问题陈述"),
            ("evidence", "科学证据"),
            ("product", "产品衔接"),
            ("monetization", "赚钱逻辑"),
            ("closing", "收尾"),
        ]:
            if outline.get(key):
                blocks.append(_p(f"【{label}】{outline[key]}"))
        blocks.append(
            _p(
                f"五维评分: {item.get('score','')} | 合规: {item.get('compliance','🟢')}"
            )
        )
        if item.get("improvement_suggestions"):
            blocks.append(_p("改进建议:", bold=True))
            for s in item["improvement_suggestions"]:
                blocks.append(_bullet(s))
        blocks.append(_divider())
    return blocks


def build_doc_c_blocks(sid: str) -> list:
    """云文档 C: 全文 + 配图 + 排版预审"""
    article_path = ARTIFACTS_DIR / sid / "step3-article.md"
    article = article_path.read_text() if article_path.exists() else "(暂无正文)"
    imgs_meta_path = ARTIFACTS_DIR / sid / "step4-images" / "meta.json"
    imgs_meta = (
        json.loads(imgs_meta_path.read_text()) if imgs_meta_path.exists() else {}
    )

    blocks = [
        _p(f"会话: {sid}  |  预审阶段: 全文 + 配图 + 排版"),
        _divider(),
        _h2("全文正文"),
    ]
    for para in article.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("# "):
            blocks.append(_h2(para[2:]))
        elif para.startswith("## "):
            blocks.append(_h3(para[3:]))
        elif para.startswith("---"):
            blocks.append(_divider())
        else:
            blocks.append(_p(para))

    if imgs_meta:
        blocks.append(_h2("配图清单"))
        if imgs_meta.get("cover"):
            blocks.append(_p(f"封面: {imgs_meta['cover'].get('path','?')}"))
        for fig in imgs_meta.get("figures", []):
            blocks.append(
                _p(f"[{fig.get('position','?')}] {fig.get('path','?')} — {fig.get('caption','')}")
            )

    return blocks


BUILDERS = {
    1: ("A · 选题预审", build_doc_a_blocks),
    2: ("B · 标题大纲预审", build_doc_b_blocks),
    5: ("C · 全文+配图+排版预审", build_doc_c_blocks),
}


def publish(sid: str, step: int) -> str:
    if step not in BUILDERS:
        raise ValueError(f"不支持 step={step}(只支持 1/2/5)")
    label, builder = BUILDERS[step]
    title = f"[日生研] {label} · {sid}"
    token = _tenant_token()
    doc_id = _create_doc(token, title)
    blocks = builder(sid)
    _append_blocks(token, doc_id, blocks)
    _grant(token, doc_id, os.environ.get("TARGET_OPEN_ID", ""))
    url = f"https://bytedance.feishu.cn/docx/{doc_id}"

    # 回写 session.json
    sessions_dir = SKILL_DIR / "scripts" / "interactive" / "sessions"
    sf = sessions_dir / f"{sid}.json"
    if sf.exists():
        data = json.loads(sf.read_text())
        data.setdefault("docs", {})[str(step)] = {
            "url": url,
            "doc_id": doc_id,
            "published_at": datetime.now().isoformat(),
        }
        sf.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    print(url)
    return url


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pub = sub.add_parser("publish")
    pub.add_argument("--sid", required=True)
    pub.add_argument("--step", type=int, choices=[1, 2, 5], required=True)
    args = p.parse_args()
    if args.cmd == "publish":
        publish(args.sid, args.step)


if __name__ == "__main__":
    main()
