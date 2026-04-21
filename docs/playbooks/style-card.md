# Playbook：排版主题选择卡

> 场景：用户首次使用或想更换文章排版风格时，弹出主题选择卡，支持 10 个推荐主题快速选择，或展开全部 31 个兜底主题。

---

## 10 个推荐主题

| 编号 | 主题 ID | 中文名 | 适合场景 |
|------|---------|--------|----------|
| 1 | `mint-fresh` | 薄荷清新 | 健康科普，清爽专业，**默认** |
| 2 | `warm-health` | 暖色健康 | 老年人群，温暖亲切 |
| 3 | `professional-blue` | 专业蓝 | 数据类文章，可信权威 |
| 4 | `sage-green` | 鼠尾草绿 | 养生类，自然质朴 |
| 5 | `clean-white` | 极简白 | 长文阅读，减少干扰 |
| 6 | `warm-brown` | 暖棕系 | 故事类，人情味强 |
| 7 | `coral-energy` | 珊瑚活力 | 招商类，积极进取 |
| 8 | `deep-forest` | 深绿森林 | 高端科研，厚重感 |
| 9 | `soft-lavender` | 薰衣草紫 | 女性用户，柔和亲切 |
| 10 | `ocean-calm` | 海洋静谧 | 情绪类，安抚平静 |

---

## 首次配置

### 在 config.json 写入 preferred_theme

用户首次选择后，写入配置文件持久化：

```bash
python3 -c "
import json, os
config_path = os.path.expanduser('~/.nsksd-content/config.json')
config = json.load(open(config_path))
config.setdefault('settings', {})['preferred_theme'] = 'mint-fresh'  # 替换为用户选择
json.dump(config, open(config_path, 'w'), ensure_ascii=False, indent=2)
print('主题已保存：mint-fresh')
"
```

### 通过 setup_cli.py 设置

```bash
python3 scripts/setup_cli.py
# 运行后可以看到 preferred_theme 字段，直接修改
```

---

## 触发弹卡

### 触发正则（style_card_trigger）

以下用户输入会触发排版选择卡：

```python
STYLE_CARD_TRIGGERS = [
    r"换(个|一个|个)?排版",
    r"换(个|一个)?主题",
    r"换(个|一个)?风格",
    r"排版(太|不|有点|感觉)",
    r"主题(太|不|有点|感觉)",
    r"改(一下)?排版",
    r"选(个|一个)?排版",
    r"用.*主题",
    r"换.*样式",
]
```

### 用户说"换排版"时弹卡

```python
# 在 lark_ws_listener.py 里处理
import re

def check_style_trigger(message: str) -> bool:
    triggers = [
        r"换(个|一个)?排版", r"换(个|一个)?主题", r"换(个|一个)?风格",
        r"改(一下)?排版", r"选(个|一个)?排版", r"用.*主题",
    ]
    return any(re.search(t, message) for t in triggers)

# 如果触发，发送排版选择卡
if check_style_trigger(user_message):
    send_style_card(chat_id=open_chat_id)
```

---

## 排版选择卡结构

```python
def build_style_card(show_all: bool = False) -> dict:
    themes_10 = [
        {"text": "薄荷清新（默认）", "value": "mint-fresh"},
        {"text": "暖色健康", "value": "warm-health"},
        {"text": "专业蓝", "value": "professional-blue"},
        {"text": "鼠尾草绿", "value": "sage-green"},
        {"text": "极简白", "value": "clean-white"},
        {"text": "暖棕系", "value": "warm-brown"},
        {"text": "珊瑚活力", "value": "coral-energy"},
        {"text": "深绿森林", "value": "deep-forest"},
        {"text": "薰衣草紫", "value": "soft-lavender"},
        {"text": "海洋静谧", "value": "ocean-calm"},
    ]
    # show_all=True 时加载全部 31 个主题，来源：references/themes-curated.md
    return {
        "schema": "2.0",
        "body": {
            "direction": "vertical",
            "elements": [
                {"tag": "markdown", "content": "**选择排版主题**\n\n以下 10 个为推荐主题"},
                {
                    "tag": "form",
                    "name": "style_form",
                    "elements": [
                        {
                            "tag": "select_static",
                            "name": "chosen_theme",
                            "placeholder": "选择主题...",
                            "options": [
                                {"text": {"tag": "plain_text", "content": t["text"]},
                                 "value": t["value"]}
                                for t in themes_10
                            ]
                        },
                        {"tag": "button", "action_type": "form_submit",
                         "text": {"tag": "plain_text", "content": "确认"}},
                        {"tag": "button", "action_type": "callback",
                         "value": {"action": "show_all_themes"},
                         "text": {"tag": "plain_text", "content": "查看全部 31 个"}},
                    ]
                }
            ]
        }
    }
```

---

## 用户点"查看全部 31 个"

callback 触发后，重新发送卡片，options 改为全部 31 个主题。全部主题列表来源：`references/themes-curated.md`。

```python
def handle_style_callback(action: dict, chat_id: str):
    if action.get("value", {}).get("action") == "show_all_themes":
        full_card = build_style_card(show_all=True)
        send_card(chat_id=chat_id, card=full_card)
```

---

## 常见错误

### 用户选了主题但没生效

**检查：**
1. `~/.nsksd-content/config.json` 里 `settings.preferred_theme` 是否已更新
2. 生成文章时是否读取了该配置（`nsksd_publish.py` 里的 `get_theme()` 函数）

### 主题 ID 不认识

所有有效主题 ID 在 `references/themes-curated.md` 里。输入无效 ID 时，降级使用 `mint-fresh`。

---

## 验证方法

```bash
# 查看当前 preferred_theme
python3 -c "
import json, os
config = json.load(open(os.path.expanduser('~/.nsksd-content/config.json')))
print('当前主题：', config.get('settings', {}).get('preferred_theme', '未设置'))
"
```

---

## 回查兜底

主题文件缺失时，所有文章使用 `mint-fresh` 默认主题，不报错，不中断流水线。
