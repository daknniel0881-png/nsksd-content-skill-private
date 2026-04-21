"""日生研 NSKSD · 飞书卡片构建器(v4 定版,唯一入口)

只保留三种卡片:
1. multi_choice_card()  — 每日多选卡(选项并列平铺 + 点选 + 提交)
2. notify_card()        — 纯通知卡(无交互,撰写中/已发布 等状态)
3. build_locked_choice_card() — 提交后的锁定态(listener 内部复用)

历史设计:以前还有 feedback_card / confirm_card / multi_choice_card(下拉版)
等多种形态。v4 起全部废弃,每日推送统一只用 multi_choice_card(v4 平铺版)。
"""
import json
from typing import Optional


# ============ 1. 每日多选卡(唯一入口) ============

def multi_choice_card(
    session_id: str,
    step: str,
    title: str,
    intro_md: str,
    options: list,
    submit_label: str = "✅ 确认选择 · 开始撰写",
    header_template: str = "turquoise",
    subtitle: str = "勾选选题后,点底部按钮一次提交",
) -> dict:
    """每日多选卡(v4 定版 · 选项并列平铺 · 点选+提交)

    Args:
        session_id: 会话唯一 id(例 2026-04-21-ffc-daily)
        step: 步骤标识(例 topic_select)
        title: 卡片标题
        intro_md: 引导语 Markdown
        options: 选项列表 [{value, text}, ...] 按原序渲染(必须 >= 10)
        submit_label: 提交按钮文案
        header_template: turquoise(原始)/grey(锁定)/yellow(撰写中)/green(完成)
        subtitle: 副标题

    关键设计:
    - 每个 option 渲染为独立 checker 元素(name=opt_{value})
    - 提交按钮 form_action_type=submit + behaviors[callback]
    - behaviors.value 内塞入 options + original_title,供锁定卡反查原序原文案
    - 所有字段写死不允许调用方改 JSON 结构

    选项数量下限 10(曲率硬约束,少于 10 个抛错)
    """
    if len(options) < 10:
        raise ValueError(f"每日多选卡选项必须 >= 10 个,当前 {len(options)}")

    # 按原序渲染 checker(核心:绝不依赖 form_value 字典序)
    checker_elements = [
        {
            "tag": "checker",
            "name": f"opt_{o['value']}",
            "text": {"tag": "lark_md", "content": o["text"]},
            "checked": False,
        }
        for o in options
    ]

    # button.behaviors.value:塞入 options 便于锁定卡反查
    button_value = {
        "action": "choose",
        "session_id": session_id,
        "step": step,
        "options": options,
        "original_title": title,
    }

    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": intro_md},
                {"tag": "hr"},
                {
                    "tag": "form",
                    "name": "choice_form",
                    "elements": [
                        *checker_elements,
                        {"tag": "hr"},
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": submit_label},
                            "type": "primary",
                            "width": "fill",
                            "form_action_type": "submit",
                            "name": "submit_btn",
                            "behaviors": [{"type": "callback", "value": button_value}],
                        },
                    ],
                },
            ]
        },
    }


# ============ 2. 通知卡(撰写中/已发布 等状态) ============

def notify_card(
    title: str,
    content_md: str,
    header_template: str = "blue",
    subtitle: str = "",
) -> dict:
    """纯通知卡 · 无交互

    用途:
    - 撰写中    → header_template="yellow"
    - 已推送草稿 → header_template="green"
    - 出错       → header_template="red"
    """
    header = {
        "template": header_template,
        "title": {"tag": "plain_text", "content": title},
    }
    if subtitle:
        header["subtitle"] = {"tag": "plain_text", "content": subtitle}
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": header,
        "body": {
            "elements": [
                {"tag": "markdown", "content": content_md},
            ]
        },
    }


# ============ 3. 锁定态卡(提交后替换原消息) ============

def build_locked_choice_card(
    options: list,
    form_value: dict,
    original_title: str = "",
) -> dict:
    """多选卡的锁定态 · 保留原序原文案 + 灰化 + 标注已选

    listener 在收到 submit callback 后 return 这张卡替换原消息。
    绝对不依赖 form_value 字典序(坑 1:sorted 会让 topic_10 跳到 topic_2 前)。
    """
    checker_elements = []
    chosen_titles = []
    for opt in options:
        opt_key = f"opt_{opt['value']}"
        picked = bool(form_value.get(opt_key, False))
        mark = "✅" if picked else "⬜"
        checker_elements.append({
            "tag": "checker",
            "text": {"tag": "lark_md", "content": f"{mark}  {opt['text']}"},
            "checked": picked,
            "disabled": True,
        })
        if picked:
            chosen_titles.append(opt["text"])

    chosen_md = "\n".join(f"• {t}" for t in chosen_titles) if chosen_titles \
        else "(未勾选任何选项)"
    header_title = f"{original_title} · 已锁定" if original_title \
        else "日生研NSKSD · 选题多选 · 已锁定"
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": "grey",
            "title": {"tag": "plain_text", "content": header_title},
            "subtitle": {"tag": "plain_text",
                         "content": f"已提交 {len(chosen_titles)} 个选题 · 不可再交互"},
        },
        "body": {
            "elements": [
                *checker_elements,
                {"tag": "hr"},
                {"tag": "markdown",
                 "content": f"**✅ 已选择**\n\n{chosen_md}\n\n⏳ Claude Code 已接单,进入撰写流水线"},
                {"tag": "button",
                 "text": {"tag": "plain_text", "content": "✅ 已提交 · 处理中"},
                 "type": "default", "disabled": True, "width": "fill"},
            ]
        },
    }


# ============ CLI 测试入口 ============

if __name__ == "__main__":
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else "multi"
    if kind == "multi":
        opts = [{"value": f"t{i}", "text": f"示例选题 {i}"} for i in range(1, 11)]
        card = multi_choice_card(
            session_id="test-001",
            step="topic_select",
            title="日生研NSKSD · 每日选题多选",
            intro_md="💡 勾选你要创作的选题",
            options=opts,
        )
    elif kind == "notify":
        card = notify_card(
            title="⏳ 正在撰写 3 篇",
            content_md="• 选题 A\n• 选题 B\n• 选题 C",
            header_template="yellow",
        )
    elif kind == "locked":
        opts = [{"value": f"t{i}", "text": f"示例选题 {i}"} for i in range(1, 11)]
        fv = {f"opt_t{i}": (i in [1, 3, 5]) for i in range(1, 11)}
        card = build_locked_choice_card(opts, fv, "日生研NSKSD · 每日选题多选")
    else:
        print(f"未知类型: {kind}")
        sys.exit(1)
    print(json.dumps(card, ensure_ascii=False, indent=2))
