# 飞书卡片推送系统

> 本文档详细说明飞书卡片设计、回调机制、WSClient长连接服务的技术细节。

## 每日选题推送流程

每天早上10点，定时脚本自动执行以下流程：

```
STEP 1: Claude CLI 生成10个选题（含S/A/B分级、五维评分、合规预检）
STEP 2: 创建飞书云文档（写入选题详情，设置用户可访问）
STEP 3: 启动WSClient长连接监听服务（注册选题到内存）
STEP 4: 通过监听服务HTTP端口依次发送两张卡片（清单卡 + 多选卡）
```

## 卡片设计（两张卡片）

### 第一张：📋 选题清单卡（绿色，schema 1.0）

纯展示卡片，不需要表单回调：
- 按 S/A/B 等级分组列出所有选题概览
- 每个选题显示：序号、标题（加粗）、内容线、评分、合规标记、一句话摘要
- 等级之间用 `hr` 分割线
- 底部一个「📄 查看完整选题方案」按钮（`multi_url` 跳转飞书云文档）
- 飞书云文档包含每个选题的详细构思：核心角度、目标人群、备选标题、大纲框架等
- HTTP端点：`POST /send-summary-card`，body可传 `{ "doc_url": "..." }`

**为什么用 schema 1.0**：清单卡是纯展示，需要 `action` tag 放置跳转按钮。schema 2.0 不支持 `action` tag（会报错），所以清单卡用 1.0。

### 第二张：📝 多选选题卡（蓝色，schema 2.0）

核心交互卡片，用户在这里选题并触发写稿流程：
- 使用 `form` 容器包裹所有交互元素
- 按 S/A/B 等级分组，每组有加粗 markdown 标题（🏆 S级 / ⭐ A级 / 📌 B级）
- 每个选题用 `checker` 组件（form 内，**不配 behaviors**，避免200672错误）
- checker 的 text 显示两行：第一行 `内容线（分数）合规标记  标题`，第二行 `一句话摘要`
- 等级之间用 `hr` 分割线
- 底部一个 `button`（`form_action_type: "submit"`），点击提交整个 form
- **用户提交后卡片自动变灰**：header 变 grey，按钮和 checker 全部 disabled
- HTTP端点：`POST /send-card`

## 关键技术点（踩坑记录）

### schema 1.0 vs 2.0
- schema 1.0：支持 `action` tag，按钮跳转用 `multi_url`
- schema 2.0：**不支持 `action` tag**（报错 200861），按钮跳转用 `behaviors: [{ type: "open_url" }]`
- 需要 form + checker 交互 → 必须用 schema 2.0
- 只需要按钮跳转链接 → 用 schema 1.0 更简单

### checker 在 form 内的限制
- **不能配 behaviors**（否则报 200672 错误）
- checker 只靠 form 提交按钮统一触发回调
- 提交按钮必须设置 `form_action_type: "submit"`，不是普通 button

### card.action.trigger 回调
- 用户点提交 → 飞书通过 WSClient 长连接推送 `card.action.trigger` 事件
- 回调的 `action.form_value` 格式：`{ "topic_1": true, "topic_3": true, "topic_5": false, ... }`
- **回调处理必须在3秒内返回**（写稿等重操作用 `.catch()` 异步处理）
- 返回值中 `card.type: "raw"` + `card.data: 新卡片JSON` 可以原地更新卡片

### 卡片变灰机制
回调返回时调用 `buildSelectCard(currentTopics, true)`，`disabled=true` 参数触发：
- `header.template` 从 `"blue"` 变为 `"grey"`
- `header.subtitle` 变为 "已提交，文案创作中..."
- 所有 checker 组件加 `disabled: true`
- 提交按钮加 `disabled: true`，文字变为 "✅ 已提交，正在生成..."

## 多选卡回调 → 写稿 → 排版 → 推送草稿箱

```
用户在清单卡查看选题详情 → 在多选卡勾选要写的选题 → 点「📝 提交选题，开始创作」
    ↓
card.action.trigger 回调 → 解析 form_value 中 value===true 的 checker
    ↓
返回 toast "已提交X个选题" + 更新卡片（按钮变灰、header变灰）
    ↓
异步 handleTopicSelection()：
    ↓
发送橙色「⏳ 正在生成文稿...」进度卡片（列出选中的选题）
    ↓
逐篇执行：
  1. Claude CLI 写稿（claude -p，只输出纯 Markdown 文章，不含对话内容）
  2. format.py 排版（自动选主题，见 docs/formatting.md 主题映射表）
  3. publish.py 推送草稿箱（自动放入默认封面图，非交互模式）
    ↓
发送绿色/橙色「✅ 全部完成，已推送草稿箱」通知卡片
  - 每篇显示状态：已推送草稿箱 / 排版失败 / 推送失败
  - 底部「📝 前往公众号草稿箱」按钮（open_url 跳转 mp.weixin.qq.com）
```

## Claude CLI 写稿 prompt 要点

```
- 角色：微信公众号文案写手
- 先读 SKILL.md + references/ 获取素材
- 只输出纯 Markdown 文章正文（1500-2500字）
- 第一行必须是 # 标题，最后一行是正文结尾
- 段落之间必须空一行，保持简洁干净的排版节奏
- 禁止输出评分、声明、免责尾注等AI痕迹（详见 docs/formatting.md 干净草稿要求）
- 禁止输出任何非文章内容（不要"好的""收到"、不要分析过程、不要合规自查表）
```

## 长连接服务（WSClient模式）

服务端代码：`scripts/server/index.ts`，基于飞书SDK WSClient长连接模式。

**核心优势**：不需要公网IP、不需要内网穿透、不需要Nginx。

同时监听两种事件：
- `card.action.trigger`（卡片回调）
- `im.message.receive_v1`（文本消息备选）

### HTTP管理端口（默认9800）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/send-summary-card` | POST | 发送清单卡片，body: `{ "doc_url": "...", "open_id": "..." }` |
| `/send-card` | POST | 发送多选卡片，body: `{ "open_id": "..." }` |
| `/set-doc-url` | POST | 设置飞书云文档URL，body: `{ "doc_url": "..." }` |
| `/register-topics` | POST | 注册选题，body: `{ "topics": [...] }` |
| `/health` | GET | 健康检查 |
| `/status` | GET | 查看当前选题和生成状态 |

### 启动命令

```bash
cd scripts/server && source .env && bun run index.ts
```

## 注意事项

- WSClient 连接在服务重启后会自动重连
- 如果服务未运行时用户点了卡片，回调会丢失（WSClient 架构限制）
- 卡片发送后有去重机制，同一张卡片不会重复发送
- 写稿过程中如果服务重启，正在生成的文章会丢失，需要重新提交
