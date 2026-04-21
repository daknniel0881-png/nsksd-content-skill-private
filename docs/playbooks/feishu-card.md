# Playbook：飞书交互卡片

> 场景：通过飞书卡片向用户推送选题多选卡，接收用户勾选后触发撰写流水线。

---

## 场景说明

NSKSD 内容流水线使用飞书卡片（schema 2.0）作为用户交互界面。核心是多选卡，用户勾选选题后点提交，触发 trigger 文件 → trigger-watcher → claude -p 撰写流水线。

---

## 步骤

### 1. 获取凭证

凭证来自 `~/.nsksd-content/config.json`（由 `setup_cli.py` 引导填写）：

```json
{
  "lark": {
    "app_id": "cli_...",
    "app_secret": "...",
    "target_open_id": "oc_...",
    "customer_open_chat_id": "oc_..."
  }
}
```

**凭证获取方式：**
- `app_id` / `app_secret`：飞书开放平台 → 应用管理 → 选择应用 → 凭证与基础信息
- `target_open_id`：机器人对话的 open_id，通过飞书 IM 的 `message.receive` 事件获取
- `customer_open_chat_id`：群聊 chat_id，通过飞书 IM 的群聊 API 或 `chat.created` 事件获取

### 2. chat_id 获取方法

```bash
# 方法一：lark-cli 查群列表（需要机器人在群里）
lark-cli im +chats-list

# 方法二：通过飞书开放平台 API Explorer
# https://open.feishu.cn/api-explorer/cli_xxx/im/v1/chats/list
```

### 3. 推送多选卡

```python
# 由 scripts/interactive/send_notify.py 负责
python3 scripts/interactive/send_notify.py \
  --chat-id "oc_xxx" \
  --kind start \
  --titles "选题1,选题2,选题3"
```

### 4. 卡片 schema 2.0 结构

NSKSD 卡片使用 `form` 容器 + `checkbox_group` 组件：

```json
{
  "schema": "2.0",
  "body": {
    "direction": "vertical",
    "elements": [
      {
        "tag": "form",
        "name": "topic_form",
        "elements": [
          {
            "tag": "checkbox_group",
            "name": "chosen_ids",
            "options": [
              {"text": {"tag": "plain_text", "content": "选题1"}, "value": "topic_1"}
            ]
          },
          {
            "tag": "button",
            "action_type": "form_submit",
            "text": {"tag": "plain_text", "content": "确认选择"}
          }
        ]
      }
    ]
  }
}
```

---

## 乱码防护

乱码来自 7 个源头，`scripts/server/utils/text-sanitizer.ts` 全部处理：

| 来源 | 处理方式 |
|------|----------|
| BOM（字节序标记）| 剥除 |
| 零宽字符 | 删除 |
| CRLF | 统一转 LF |
| 控制字符（ASCII 0-31 除 LF/TAB）| 删除 |
| UTF-8 字节截断 | 回退至起始字节 |
| option.value 特殊字符 | 替换为下划线 |
| Content-Type charset 缺失 | 强制 `application/json; charset=utf-8` |

**验证乱码防护（单测）：**

```bash
cd /Users/suze/.claude/skills/nsksd-content
bun test scripts/server/utils/text-sanitizer.test.ts
# 应显示 13 tests passed
```

---

## trigger 文件流

```
用户提交卡片
  ↓
lark_ws_listener.py 收到回调
  ↓
写 triggers/<session_id>.trigger（包含 chosen_titles, chosen_ids, open_chat_id）
  ↓
trigger_watcher.sh 检测到新 trigger（每 5s 轮询）
  ↓
标记 status=running
  ↓
调 claude -p 运行撰写流水线
  ↓
成功: mv 到 triggers/done/
失败: mv 到 triggers/failed/ + 推送失败通知
```

### trigger 文件格式

```json
{
  "session_id": "daily-2026-04-21",
  "chosen_titles": ["标题1", "标题2"],
  "chosen_ids": ["topic_1", "topic_3"],
  "open_chat_id": "oc_xxx",
  "status": "running",
  "started_at": "2026-04-21T10:30:00"
}
```

---

## 常见错误

### 卡片推送但不显示

**检查：**
1. `app_id` 对应的机器人是否在目标群/会话里
2. `customer_open_chat_id` 是否正确（用 lark-cli 查验）
3. 卡片 JSON 是否有语法错误（用 `python3 -c "import json; json.load(open('card.json'))"` 验证）

### 用户点提交但 trigger 文件未生成

**检查：**
1. `lark_ws_listener.py` 是否在运行（`cat /tmp/nsksd-listener.pid` 看 PID，`kill -0 <PID>` 验证）
2. 飞书 App 的 Event Subscribe 是否配置了 `im.message.receive_v1`
3. WebSocket 连接日志：`tail -f logs/listener-$(date +%F).log`

### trigger-watcher 停了

```bash
# 手动重启
cd /Users/suze/.claude/skills/nsksd-content/scripts/interactive
nohup bash trigger_watcher.sh > /tmp/nsksd-watcher-manual.log 2>&1 &
echo $! > /tmp/nsksd-watcher.pid
```

---

## 验证方法

1. 手动测试推卡：`python3 scripts/interactive/send_notify.py --chat-id oc_xxx --kind test`
2. 手动触发 trigger：创建一个测试 trigger 文件，检查 watcher 是否捡起
3. 验证卡片内容：推送后在飞书查看卡片是否正确显示

---

## 回查兜底

飞书卡片推送失败时：
1. 检查 `logs/listener-<date>.log` 排查 WebSocket 问题
2. 手动重启 listener 和 watcher（见上方命令）
3. 如果用户已口头告知选题，可手动创建 trigger 文件绕过卡片交互
