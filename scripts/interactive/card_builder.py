"""日生研内容创作 · 飞书交互卡片构建器

提供三类卡片模板:
1. feedback_card()   — 带输入框的修改意见卡(打磨模式每步都用)
2. multi_choice_card() — 多选卡(选题勾选 / 排版主题精选)
3. confirm_card()    — 确认推送卡(最终步)

所有卡片都遵循:
- schema 2.0
- form 容器 + form_action_type=submit 按钮(input 值才能回传)
- button value 带 session_id + step,方便监听器写对会话

配套使用:
    from card_builder import feedback_card
    card = feedback_card(
        session_id="2026-04-20-001",
        step="title_outline",
        title="第2步 · 标题与大纲确认",
        preview_md="已生成标题:XXX\\n大纲:...",
        doc_url="https://...feishu.cn/docx/xxx"
    )
    # 用 lark-cli 发卡:
    # lark-cli im +messages-send --msg-type interactive --content '{json}'
"""
import json
from typing import Optional


def feedback_card(
    session_id: str,
    step: str,
    title: str,
    preview_md: str,
    doc_url: Optional[str] = None,
    subtitle: str = "请输入修改意见后提交,或留空表示认可",
    submit_label: str = "✅ 提交修改意见",
    header_template: str = "blue",
) -> dict:
    """打磨模式 · 带输入框的修改意见卡"""
    elements = [
        {"tag": "markdown", "content": preview_md},
    ]
    if doc_url:
        elements.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📄 打开云文档预览"},
            "type": "default",
            "width": "default",
            "multi_url": {"url": doc_url, "pc_url": doc_url, "android_url": doc_url, "ios_url": doc_url},
        })
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "form",
        "name": "feedback_form",
        "elements": [
            {
                "tag": "input",
                "name": "user_feedback",
                "placeholder": {"tag": "plain_text", "content": "请输入修改意见(留空表示认可,直接进入下一步)"},
                "default_value": "",
                "width": "fill",
                "required": False,
                "label": {"tag": "plain_text", "content": "修改意见"},
                "label_position": "top",
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": submit_label},
                "type": "primary",
                "width": "default",
                "form_action_type": "submit",
                "name": "submit_btn",
                "behaviors": [{
                    "type": "callback",
                    "value": {
                        "action": "submit",
                        "session_id": session_id,
                        "step": step,
                        "_original_body_md": preview_md,
                    },
                }],
            },
        ],
    })

    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
        },
        "body": {"elements": elements},
    }


def multi_choice_card(
    session_id: str,
    step: str,
    title: str,
    intro_md: str,
    options: list,
    multi: bool = True,
    submit_label: str = "✅ 确认选择",
    header_template: str = "turquoise",
) -> dict:
    """多选卡 · 选题勾选 / 排版主题精选

    options: [{"value": "topic_1", "text": "选题1标题"}, ...]
    """
    select_element = {
        "tag": "select_static" if not multi else "multi_select_static",
        "name": "choices",
        "placeholder": {"tag": "plain_text", "content": "请选择..."},
        "options": [
            {"text": {"tag": "plain_text", "content": o["text"]}, "value": o["value"]}
            for o in options
        ],
    }
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": "勾选后点提交"},
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": intro_md},
                {"tag": "hr"},
                {
                    "tag": "form",
                    "name": "choice_form",
                    "elements": [
                        select_element,
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": submit_label},
                            "type": "primary",
                            "form_action_type": "submit",
                            "name": "submit_btn",
                            "behaviors": [{
                                "type": "callback",
                                "value": {
                                    "action": "choose",
                                    "session_id": session_id,
                                    "step": step,
                                },
                            }],
                        },
                    ],
                },
            ]
        },
    }


def confirm_card(
    session_id: str,
    step: str,
    title: str,
    summary_md: str,
    confirm_label: str = "🚀 推送到草稿箱",
    cancel_label: str = "取消",
    header_template: str = "red",
) -> dict:
    """最终确认卡 · 一键推送 / 取消"""
    return {
        "schema": "2.0",
        "config": {"update_multi": True, "width_mode": "default"},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": "请确认内容后推送"},
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": summary_md},
                {"tag": "hr"},
                {
                    "tag": "column_set",
                    "columns": [
                        {
                            "tag": "column", "width": "weighted", "weight": 1,
                            "elements": [{
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": confirm_label},
                                "type": "danger",
                                "behaviors": [{
                                    "type": "callback",
                                    "value": {
                                        "action": "confirm",
                                        "session_id": session_id,
                                        "step": step,
                                    },
                                }],
                            }],
                        },
                        {
                            "tag": "column", "width": "weighted", "weight": 1,
                            "elements": [{
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": cancel_label},
                                "type": "default",
                                "behaviors": [{
                                    "type": "callback",
                                    "value": {
                                        "action": "cancel",
                                        "session_id": session_id,
                                        "step": step,
                                    },
                                }],
                            }],
                        },
                    ],
                },
            ]
        },
    }


# ---- CLI 测试入口 ----
if __name__ == "__main__":
    import sys
    card_type = sys.argv[1] if len(sys.argv) > 1 else "feedback"
    if card_type == "feedback":
        card = feedback_card(
            session_id="test-001",
            step="title_outline",
            title="第2步 · 标题与大纲",
            preview_md="**标题**: 测试标题\n\n**大纲**:\n1. 一级\n2. 二级",
            doc_url="https://example.feishu.cn/docx/test",
        )
    elif card_type == "choice":
        card = multi_choice_card(
            session_id="test-001",
            step="topic_select",
            title="第1步 · 选题勾选",
            intro_md="请勾选你要创作的选题(1-3 个):",
            options=[
                {"value": "t1", "text": "选题1:AI 如何改变..."},
                {"value": "t2", "text": "选题2:某某新研究..."},
            ],
        )
    elif card_type == "confirm":
        card = confirm_card(
            session_id="test-001",
            step="publish",
            title="最终确认 · 推送草稿箱",
            summary_md="标题:测试\n字数:2500\n配图:3",
        )
    else:
        print(f"未知类型: {card_type}")
        sys.exit(1)
    print(json.dumps(card, ensure_ascii=False, indent=2))
