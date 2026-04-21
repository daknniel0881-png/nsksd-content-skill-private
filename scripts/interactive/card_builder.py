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


# ============ 4. Guided 逐步反馈卡（V9.5 引导模式） ============

def build_guided_feedback_card(
    session_id: str,
    step_name: str,
    step_index: int,
    total_steps: int,
    step_output_md: str,
    header_title: str = "",
) -> dict:
    """引导模式 · 每步反馈卡

    用途：撰写流水线每完成一步（title-outliner / article-writer /
    quyu-view-checker / image-designer / format-publisher）都推一张这种卡，
    曲率审核后二选一：打回修改（填输入框）或 通过到下一步。

    设计：
    - 1 个 text_input：反馈/修改意见（打回必填，通过可空）
    - 2 个 button（在同一 form 内，form_action_type=submit）：
      · 🔴 打回修改（danger，value.action="reject"）
      · 🟢 通过到下一步（primary，value.action="approve"）
    - button.value 带 session_id + step_name + step_index，listener 侧据此
      写 feedback 文件给 trigger_watcher，trigger_watcher 按 action 决定
      重跑当前 Agent 还是进下一步

    Args:
        session_id: 会话 id（例 test-v95-guided-001）
        step_name: 步骤英文标识（例 title_outliner）
        step_index: 当前是第几步（1-based）
        total_steps: 总步数（例 5）
        step_output_md: 当前步骤的产出内容（Markdown，给曲率审核）
        header_title: 卡片头标题（留空会自动拼）
    """
    default_title = f"🧭 引导模式 · 第 {step_index}/{total_steps} 步 · {step_name}"
    title = header_title or default_title

    # button.value 骨架（≤2KB 限制）：只塞 header + step_output_md，
    # 不塞整个 body.elements。listener 侧 patch 时按骨架重建。
    card_skeleton = {
        "title": title,
        "subtitle": "审核产出 → 打回修改 或 通过到下一步",
        "step_output_md": step_output_md,
    }
    approve_value = {
        "action": "approve",
        "session_id": session_id,
        "step_name": step_name,
        "step_index": step_index,
        "total_steps": total_steps,
        "_skeleton": card_skeleton,
    }
    reject_value = {
        "action": "reject",
        "session_id": session_id,
        "step_name": step_name,
        "step_index": step_index,
        "total_steps": total_steps,
        "_skeleton": card_skeleton,
    }

    # 布局：input 全宽 + column_set 左右双 button（曲率验收左右布局）
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text",
                         "content": "审核产出 → 打回修改 或 通过到下一步"},
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": "### 本步产出\n\n" + step_output_md},
                {"tag": "hr"},
                {
                    "tag": "form",
                    "name": "feedback_form",
                    "elements": [
                        {
                            "tag": "input",
                            "name": "feedback_text",
                            "placeholder": {
                                "tag": "plain_text",
                                "content": "填你的修改意见（打回必填，通过可空）",
                            },
                            "default_value": "",
                            "width": "default",
                            "max_length": 1000,
                        },
                        {
                            "tag": "column_set",
                            "flex_mode": "bisect",
                            "horizontal_spacing": "small",
                            "margin": "0px",
                            "columns": [
                                {
                                    "tag": "column",
                                    "width": "weighted",
                                    "weight": 1,
                                    "elements": [
                                        {
                                            "tag": "button",
                                            "text": {"tag": "plain_text",
                                                     "content": "🔴 打回修改"},
                                            "type": "primary",
                                            "width": "fill",
                                            "form_action_type": "submit",
                                            "name": "reject_btn",
                                            "behaviors": [{
                                                "type": "callback",
                                                "value": reject_value,
                                            }],
                                        },
                                    ],
                                },
                                {
                                    "tag": "column",
                                    "width": "weighted",
                                    "weight": 1,
                                    "elements": [
                                        {
                                            "tag": "button",
                                            "text": {"tag": "plain_text",
                                                     "content": "🟢 通过到下一步"},
                                            "type": "primary",
                                            "width": "fill",
                                            "form_action_type": "submit",
                                            "name": "approve_btn",
                                            "behaviors": [{
                                                "type": "callback",
                                                "value": approve_value,
                                            }],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ]
        },
    }


# ============ 5. Guided 锁定态卡（approve/reject 提交后替换原消息） ============

def build_guided_locked_card(
    skeleton: dict,
    action: str,
    feedback_text: str,
    step_name: str = "",
    step_index: int = 0,
    total_steps: int = 0,
) -> dict:
    """引导反馈卡的锁定态（B 方案 · 就地 patch 版）

    设计：不重写卡，而是基于原卡骨架（skeleton）重建：
    - header.template 改 'grey'（灰化视觉）
    - 保留 title/subtitle/step_output_md 原样（曲率要求"原样式文字布局不变"）
    - 禁用的 input 展示曲率填的意见（disabled:true）
    - 两个禁用 button 展示"✅ 已提交（已打回/已通过）"状态
    - 末尾追加一行 markdown "修改意见已提交 · HH:MM"

    Args:
        skeleton: 原卡骨架 {title, subtitle, step_output_md}
        action: "approve" | "reject"
        feedback_text: 曲率填的意见
        step_name/step_index/total_steps: 可选,用于 footer 显示
    """
    from datetime import datetime
    is_approve = action == "approve"
    status_label = "✅ 已通过 · Agent 进入下一步" if is_approve \
        else "🔴 已打回 · Agent 按意见重做中"
    feedback_display = feedback_text.strip() or "(未填写意见)"
    timestamp = datetime.now().strftime("%H:%M")

    title = skeleton.get("title", "")
    subtitle = skeleton.get("subtitle", "")
    step_output_md = skeleton.get("step_output_md", "")

    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": "grey",  # 灰化
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text",
                         "content": subtitle + " · 已锁定"},
        },
        "body": {
            "elements": [
                # 1. 原产出原样保留
                {"tag": "markdown",
                 "content": "### 本步产出\n\n" + step_output_md},
                {"tag": "hr"},
                # 2. 曲率意见展示（替代原 input 框）
                {"tag": "markdown",
                 "content": f"**📝 曲率修改意见**\n\n{feedback_display}"},
                # 3. 原双 button 结构保留,但 disabled + 改文案显示状态
                {
                    "tag": "column_set",
                    "flex_mode": "bisect",
                    "horizontal_spacing": "small",
                    "margin": "0px",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [{
                                "tag": "button",
                                "text": {"tag": "plain_text",
                                         "content": ("🔴 已打回" if not is_approve
                                                     else "🔴 打回修改")},
                                "type": "default",
                                "width": "fill",
                                "disabled": True,
                            }],
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [{
                                "tag": "button",
                                "text": {"tag": "plain_text",
                                         "content": ("🟢 已通过" if is_approve
                                                     else "🟢 通过到下一步")},
                                "type": "default",
                                "width": "fill",
                                "disabled": True,
                            }],
                        },
                    ],
                },
                {"tag": "hr"},
                # 4. 末尾追加确认段
                {"tag": "markdown",
                 "content": f"**{status_label}**\n\n⏰ 修改意见已提交 · {timestamp}"},
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
    elif kind == "guided":
        card = build_guided_feedback_card(
            session_id="test-v95-guided-001",
            step_name="title_outliner",
            step_index=1,
            total_steps=5,
            step_output_md=(
                "**候选标题（F3 悬念钩子 · 88 分）**\n"
                "45 岁查出颈动脉斑块，浙大的研究给了一个数字\n\n"
                "**大纲**\n"
                "1. 体检报告里的那行小字，到底意味着什么\n"
                "2. 浙大 ICC-PACS 研究 · 120 人双盲 12 周\n"
                "3. 5 招辨真假纳豆激酶，5 元成本 vs 300 元售价\n"
                "4. 养生馆店员 3 句话怎么说既合规又专业"
            ),
        )
    else:
        print(f"未知类型: {kind}")
        sys.exit(1)
    print(json.dumps(card, ensure_ascii=False, indent=2))
