# 飞书卡片完整操作手册

> 本文档详细记录每一种飞书卡片怎么写、怎么推送、JSON结构长什么样。
> **每一步都写清楚了，不跳过任何细节。** 不管用什么模型，按这个手册操作都能跑通。

---

## 总览：本Skill用到的飞书卡片类型

| # | 卡片类型 | 颜色 | 用途 | schema版本 |
|---|----------|------|------|------------|
| 1 | 📋 选题清单卡 | 绿色 | 展示选题概览 + 云文档链接 | 1.0 |
| 2 | 📝 多选选题卡 | 蓝色 | 勾选选题 + 提交触发写稿 | 2.0 |
| 3 | ⏳ 进度通知卡 | 橙色 | 显示"正在生成文稿" | 2.0 |
| 4 | ✅ 完成通知卡 | 绿色/橙色 | 显示生成结果 + 草稿箱链接 | 2.0 |
| 5 | ⚠️ 警告/提醒卡 | 橙色 | 任务冲突或错误提示 | 2.0 |

---

## 发送卡片的基础方法

### 方法一：通过飞书SDK（TypeScript/Bun）

这是本Skill使用的方式，通过 `@larksuiteoapi/node-sdk` 发送。

```typescript
import * as Lark from "@larksuiteoapi/node-sdk";

// 初始化客户端
const client = new Lark.Client({
  appId: "cli_a5xxxxxxxxxxxx",      // 你的 App ID
  appSecret: "xxxxxxxxxxxxxxxx",     // 你的 App Secret
  appType: Lark.AppType.SelfBuild,
});

// 发送卡片消息给个人（通过 open_id）
async function sendCardToUser(openId: string, card: object) {
  const resp = await client.im.v1.message.create({
    params: { receive_id_type: "open_id" },
    data: {
      receive_id: openId,
      msg_type: "interactive",
      content: JSON.stringify(card),
    },
  });
  return resp;
}

// 发送卡片消息到群（通过 chat_id）
async function sendCardToChat(chatId: string, card: object) {
  const resp = await client.im.v1.message.create({
    params: { receive_id_type: "chat_id" },
    data: {
      receive_id: chatId,
      msg_type: "interactive",
      content: JSON.stringify(card),
    },
  });
  return resp;
}
```

### 方法二：通过 lark-cli 命令行

```bash
# 发送纯文本消息
lark-cli --as bot im send \
  --receive-id "ou_xxxxxxxx" \
  --receive-id-type open_id \
  --msg-type text \
  --content '{"text":"你好"}'

# 发送卡片消息
lark-cli --as bot im send \
  --receive-id "ou_xxxxxxxx" \
  --receive-id-type open_id \
  --msg-type interactive \
  --content '{ JSON卡片内容 }'
```

### 方法三：通过 HTTP API（curl）

```bash
# 第1步：获取 tenant_access_token
TOKEN=$(curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"cli_a5xxxx","app_secret":"xxxxx"}' | jq -r '.tenant_access_token')

# 第2步：发送卡片
curl -X POST 'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "receive_id": "ou_xxxxxxxx",
    "msg_type": "interactive",
    "content": "{ 转义后的JSON卡片内容 }"
  }'
```

> 注意：content 字段的值是**字符串化的JSON**，不是直接嵌套JSON对象。需要 `JSON.stringify()` 或手动转义。

### 方法四：通过 WSClient 服务的 HTTP 端口

本Skill的 WSClient 服务暴露了 HTTP 端口用于发送卡片：

```bash
# 发送清单卡片
curl -X POST http://localhost:9800/send-summary-card \
  -H 'Content-Type: application/json' \
  -d '{"doc_url": "https://xxx.feishu.cn/docx/xxx"}'

# 发送多选卡片
curl -X POST http://localhost:9800/send-card \
  -H 'Content-Type: application/json' \
  -d '{}'

# 指定发送对象
curl -X POST http://localhost:9800/send-card \
  -H 'Content-Type: application/json' \
  -d '{"open_id": "ou_xxxxxxxx"}'
```

---

## 卡片1：📋 选题清单卡（绿色，schema 1.0）

### 用途
纯展示卡片，按 S/A/B 等级分组列出所有选题，底部有"查看详情"按钮跳转飞书云文档。

### 为什么用 schema 1.0
清单卡需要 `action` 标签放置跳转按钮。**schema 2.0 不支持 `action` 标签**（会报错 200861），所以清单卡必须用 1.0。

### 完整 JSON 结构

```json
{
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "📋 4月17日 选题清单"
    },
    "template": "green"
  },
  "elements": [
    {
      "tag": "markdown",
      "content": "**🏆 S级（强烈推荐）**"
    },
    {
      "tag": "markdown",
      "content": "1. **5元成本卖300，纳豆激酶市场到底有多乱？**\n品牌故事（95分）🟢　揭露行业乱象，用价格对比建立品牌信任"
    },
    {
      "tag": "markdown",
      "content": "2. **1062人、12个月、4家医院：最硬核的成绩单**\n科学信任（92分）🟡　用临床数据说话，最有说服力的科学背书"
    },
    {
      "tag": "hr"
    },
    {
      "tag": "markdown",
      "content": "**⭐ A级（推荐）**"
    },
    {
      "tag": "markdown",
      "content": "3. **4月24日杭州，纳豆激酶行业可能要变天了**\n品牌故事（87分）🟢　行业大会预热，制造紧迫感和期待"
    },
    {
      "tag": "hr"
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "📄 查看完整选题方案"
          },
          "type": "primary",
          "multi_url": {
            "url": "https://xxx.feishu.cn/docx/xxx",
            "android_url": "https://xxx.feishu.cn/docx/xxx",
            "ios_url": "https://xxx.feishu.cn/docx/xxx",
            "pc_url": "https://xxx.feishu.cn/docx/xxx"
          }
        }
      ]
    }
  ]
}
```

### 关键点

1. **header.template** 设为 `"green"` → 绿色标题栏
2. **markdown 标签**：支持加粗（`**文字**`）、换行（`\n`）
3. **hr 标签**：分割线，用于分隔不同等级
4. **action 标签**：**只有 schema 1.0 支持**，放置跳转按钮
5. **multi_url**：跳转链接，需要分别设置 url/android_url/ios_url/pc_url

### 构建代码（TypeScript）

```typescript
function buildSummaryCard(topics: Topic[], docUrl: string): object {
  const today = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric" });
  const elements: any[] = [];

  // 按等级分组
  for (const grade of ["S", "A", "B"]) {
    const group = topics.filter(t => t.grade === grade);
    if (group.length === 0) continue;

    const label = grade === "S" ? "🏆 S级（强烈推荐）"
               : grade === "A" ? "⭐ A级（推荐）"
               : "📌 B级（可选）";
    elements.push({ tag: "markdown", content: `**${label}**` });

    for (const t of group) {
      elements.push({
        tag: "markdown",
        content: `${t.index}. **${t.title}**\n${t.line}（${t.score}分）${t.compliance}　${t.summary || ""}`,
      });
    }
    elements.push({ tag: "hr" });
  }

  // 底部按钮
  if (docUrl) {
    elements.push({
      tag: "action",
      actions: [{
        tag: "button",
        text: { tag: "plain_text", content: "📄 查看完整选题方案" },
        type: "primary",
        multi_url: { url: docUrl, android_url: docUrl, ios_url: docUrl, pc_url: docUrl },
      }],
    });
  }

  return {
    header: {
      title: { tag: "plain_text", content: `📋 ${today} 选题清单` },
      template: "green",
    },
    elements,
  };
}
```

---

## 卡片2：📝 多选选题卡（蓝色，schema 2.0）

### 用途
核心交互卡片。用户在这里勾选选题并点提交，触发自动写稿流程。提交后卡片自动变灰。

### 为什么用 schema 2.0
需要 `form` 容器 + `checker` 勾选组件 + 表单提交，这些只有 schema 2.0 支持。

### 完整 JSON 结构

```json
{
  "schema": "2.0",
  "config": {
    "update_multi": true,
    "width_mode": "fill"
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "📋 日生研NSKSD · 4月17日选题（共10篇）"
    },
    "subtitle": {
      "tag": "plain_text",
      "content": "勾选后点击提交，自动生成文案并排版"
    },
    "template": "blue"
  },
  "body": {
    "direction": "vertical",
    "padding": "12px 12px 12px 12px",
    "elements": [
      {
        "tag": "form",
        "name": "topic_form",
        "elements": [
          {
            "tag": "markdown",
            "content": "**勾选要创作的选题：**"
          },
          {
            "tag": "markdown",
            "content": "**🏆 S级（强烈推荐）**"
          },
          {
            "tag": "checker",
            "name": "topic_1",
            "checked": false,
            "overall_checkable": true,
            "text": {
              "tag": "plain_text",
              "content": "品牌故事（95分）🟢  5元成本卖300，纳豆激酶市场到底有多乱？\n揭露行业乱象，用价格对比建立品牌信任"
            }
          },
          {
            "tag": "checker",
            "name": "topic_2",
            "checked": false,
            "overall_checkable": true,
            "text": {
              "tag": "plain_text",
              "content": "科学信任（92分）🟡  1062人、12个月、4家医院：最硬核的成绩单\n用临床数据说话，最有说服力的科学背书"
            }
          },
          {
            "tag": "hr"
          },
          {
            "tag": "markdown",
            "content": "**⭐ A级（推荐）**"
          },
          {
            "tag": "checker",
            "name": "topic_3",
            "checked": false,
            "overall_checkable": true,
            "text": {
              "tag": "plain_text",
              "content": "品牌故事（87分）🟢  4月24日杭州，纳豆激酶行业可能要变天了\n行业大会预热，制造紧迫感和期待"
            }
          },
          {
            "tag": "button",
            "text": {
              "tag": "plain_text",
              "content": "📝 提交选题，开始创作"
            },
            "type": "primary",
            "form_action_type": "submit",
            "name": "submit_btn"
          }
        ]
      }
    ]
  }
}
```

### 关键点（踩坑记录）

1. **必须有 `schema: "2.0"`**：没有这个字段，form 和 checker 不会生效
2. **`config.update_multi: true`**：允许卡片被更新（提交后变灰需要这个）
3. **form 容器**：所有 checker 和提交按钮必须包在 `form` 标签内
4. **checker 的 `name`**：格式为 `topic_1`, `topic_2` 等，提交时回调数据中用这个 name 作为 key
5. **checker 不能配 `behaviors`**：在 form 内的 checker 如果配了 behaviors 会报错 200672
6. **提交按钮的 `form_action_type: "submit"`**：这是触发 form 提交的关键，不是普通 button
7. **`overall_checkable: true`**：让整个 checker 区域都可以点击（而不只是勾选框）

### 卡片变灰机制

用户点击提交后，回调处理中返回更新后的卡片，实现"变灰"效果：

```typescript
// 提交后返回变灰的卡片
return {
  toast: {
    type: "success",
    content: `已提交 ${selectedCount} 个选题，开始创作...`,
  },
  card: {
    type: "raw",
    data: buildSelectCard(currentTopics, true),  // disabled=true
  },
};
```

变灰时的改动：
- `header.template`：从 `"blue"` 变为 `"grey"`
- `header.subtitle`：变为 `"已提交，文案创作中..."`
- 所有 checker：加 `disabled: true`
- 提交按钮：加 `disabled: true`，文字变为 `"✅ 已提交，正在创作中..."`

### 回调数据格式

用户点提交后，飞书通过 WSClient 长连接推送 `card.action.trigger` 事件：

```json
{
  "event": {
    "operator": {
      "open_id": "ou_xxxxxxxx"
    },
    "action": {
      "tag": "form_submit",
      "form_value": {
        "topic_1": true,
        "topic_2": false,
        "topic_3": true,
        "submit_btn": {}
      }
    }
  }
}
```

解析逻辑：
```typescript
const formValue = action.form_value || {};
const selectedValues: string[] = [];
for (const [key, value] of Object.entries(formValue)) {
  if (key.startsWith("topic_") && value === true) {
    selectedValues.push(key);  // ["topic_1", "topic_3"]
  }
}
```

> ⚠️ **回调必须在3秒内返回**。写稿等重操作必须用异步处理（`.catch()` 或 `setTimeout`），在返回 toast 后再开始。

---

## 卡片3：⏳ 进度通知卡（橙色）

### 用途
用户提交选题后，立即发送一张进度卡片，告知"正在生成文稿"。

### 完整 JSON 结构

```json
{
  "schema": "2.0",
  "config": { "update_multi": true, "width_mode": "fill" },
  "header": {
    "title": { "tag": "plain_text", "content": "⏳ 正在生成文稿..." },
    "subtitle": { "tag": "plain_text", "content": "共 3 篇，预计每篇2-5分钟" },
    "template": "orange"
  },
  "body": {
    "direction": "vertical",
    "padding": "12px 12px 12px 12px",
    "elements": [
      {
        "tag": "markdown",
        "content": "已提交以下选题，正在调用 Claude 撰写初稿：\n\n1. 5元成本卖300，纳豆激酶市场到底有多乱？\n3. 4月24日杭州，纳豆激酶行业可能要变天了\n5. 门店老板该关注这场大会的3件事\n\n完成后会发送通知，请稍候…"
      }
    ]
  }
}
```

### 构建代码

```typescript
function buildProgressCard(selectedTopics: Topic[]): object {
  const list = selectedTopics.map(t => `${t.index}. ${t.title}`).join("\n");
  return {
    schema: "2.0",
    config: { update_multi: true, width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: "⏳ 正在生成文稿..." },
      subtitle: { tag: "plain_text", content: `共 ${selectedTopics.length} 篇，预计每篇2-5分钟` },
      template: "orange",
    },
    body: {
      direction: "vertical",
      padding: "12px 12px 12px 12px",
      elements: [{
        tag: "markdown",
        content: `已提交以下选题，正在调用 Claude 撰写初稿：\n\n${list}\n\n完成后会发送通知，请稍候…`,
      }],
    },
  };
}
```

---

## 卡片4：✅ 完成通知卡（绿色/橙色）

### 用途
所有文稿生成完成后，发送结果通知，包含每篇的状态和"前往草稿箱"按钮。

### 完整 JSON 结构（全部成功时）

```json
{
  "schema": "2.0",
  "config": { "update_multi": true, "width_mode": "fill" },
  "header": {
    "title": { "tag": "plain_text", "content": "✅ 全部完成，已推送草稿箱" },
    "subtitle": { "tag": "plain_text", "content": "全部 3 篇已推送到草稿箱" },
    "template": "green"
  },
  "body": {
    "direction": "vertical",
    "padding": "12px 12px 12px 12px",
    "elements": [
      {
        "tag": "markdown",
        "content": "✅ 1. 5元成本卖300，纳豆激酶市场到底有多乱？（已推送草稿箱）\n✅ 3. 4月24日杭州，纳豆激酶行业可能要变天了（已推送草稿箱）\n✅ 5. 门店老板该关注这场大会的3件事（已推送草稿箱）\n\n所有文稿已推送到公众号草稿箱，请前往检查发布👇"
      },
      {
        "tag": "button",
        "text": { "tag": "plain_text", "content": "📝 前往公众号草稿箱" },
        "type": "primary",
        "size": "medium",
        "behaviors": [
          {
            "type": "open_url",
            "default_url": "https://mp.weixin.qq.com"
          }
        ]
      }
    ]
  }
}
```

### 完整 JSON 结构（部分失败时）

header.template 变为 `"orange"`，title 变为 `"⚠️ 文稿生成完成（部分需手动处理）"`。

每篇状态前缀：
- `✅` — 已推送草稿箱
- `⚠️` — 已排版但推送失败
- `❌` — 生成失败

### 关键点

**按钮跳转在 schema 2.0 中的写法**：
- schema 1.0 用 `action` + `multi_url`
- schema 2.0 用 `behaviors: [{ type: "open_url", default_url: "..." }]`

**不要混用**：schema 2.0 中用 `action` 标签会报错 200861。

---

## 卡片5：⚠️ 警告/提醒卡（橙色）

### 用途
当用户在上一批任务还没完成时又提交新选题，发送提醒。

### 完整 JSON 结构

```json
{
  "schema": "2.0",
  "header": {
    "title": { "tag": "plain_text", "content": "⚠️ 任务进行中" },
    "template": "orange"
  },
  "body": {
    "elements": [
      {
        "tag": "markdown",
        "content": "上一批选题还在创作中，请等待完成后再提交。"
      }
    ]
  }
}
```

---

## 自定义通知卡片：排版中/写作中/完成

如果你需要在流程中发送自定义状态通知，按以下模板构建：

### 模板：状态通知卡

```json
{
  "schema": "2.0",
  "config": { "update_multi": true, "width_mode": "fill" },
  "header": {
    "title": { "tag": "plain_text", "content": "EMOJI 标题文字" },
    "subtitle": { "tag": "plain_text", "content": "副标题" },
    "template": "颜色"
  },
  "body": {
    "direction": "vertical",
    "padding": "12px 12px 12px 12px",
    "elements": [
      {
        "tag": "markdown",
        "content": "正文内容，支持 **加粗** 和 `代码`"
      }
    ]
  }
}
```

**可用颜色**：`blue`、`green`、`orange`、`red`、`grey`、`purple`、`indigo`、`turquoise`、`violet`、`wathet`、`carmine`、`yellow`、`lime`

### 示例：正在排版通知

```json
{
  "schema": "2.0",
  "header": {
    "title": { "tag": "plain_text", "content": "🎨 正在排版..." },
    "subtitle": { "tag": "plain_text", "content": "第1篇：纳豆激酶市场分析" },
    "template": "wathet"
  },
  "body": {
    "elements": [
      { "tag": "markdown", "content": "使用主题：**mint-fresh**（薄荷绿）\n预计1分钟完成..." }
    ]
  }
}
```

### 示例：正在写作通知

```json
{
  "schema": "2.0",
  "header": {
    "title": { "tag": "plain_text", "content": "✍️ 正在撰写文章..." },
    "subtitle": { "tag": "plain_text", "content": "第2篇：1062人临床数据解读" },
    "template": "blue"
  },
  "body": {
    "elements": [
      { "tag": "markdown", "content": "正在调用 Claude 撰写初稿...\n预计2-5分钟，请稍候。" }
    ]
  }
}
```

### 示例：排版完成通知

```json
{
  "schema": "2.0",
  "header": {
    "title": { "tag": "plain_text", "content": "✅ 排版完成" },
    "subtitle": { "tag": "plain_text", "content": "第1篇已排版" },
    "template": "green"
  },
  "body": {
    "elements": [
      { "tag": "markdown", "content": "✅ **5元成本卖300，纳豆激酶市场到底有多乱？**\n主题：mint-fresh | 已推送草稿箱" }
    ]
  }
}
```

---

## WSClient 长连接：事件监听

### 监听两种事件

```typescript
const wsClient = new Lark.WSClient({
  appId: APP_ID,
  appSecret: APP_SECRET,
  loggerLevel: Lark.LoggerLevel.info,
});

wsClient.start({
  eventDispatcher: new Lark.EventDispatcher({}).register({
    // 事件1：卡片回调（用户点击卡片按钮/提交表单）
    "card.action.trigger": async (data: any) => {
      const event = data?.event || data;
      const action = event?.action || {};
      const openId = event?.operator?.open_id;
      const formValue = action?.form_value || {};

      // 解析勾选的选题
      const selected = Object.entries(formValue)
        .filter(([k, v]) => k.startsWith("topic_") && v === true)
        .map(([k]) => k);

      if (selected.length > 0) {
        // 异步处理（不阻塞3秒超时）
        handleTopicSelection(openId, selected).catch(console.error);

        // 返回 toast + 更新卡片
        return {
          toast: { type: "success", content: `已提交 ${selected.length} 个选题` },
          card: { type: "raw", data: buildSelectCard(currentTopics, true) },
        };
      }

      return {};
    },

    // 事件2：文本消息（用户直接回复数字选择选题）
    "im.message.receive_v1": async (data: any) => {
      const message = data.message;
      if (message.message_type !== "text") return;

      const content = JSON.parse(message.content);
      const text = content.text?.trim();
      // 解析数字编号，如 "1 3 5" 或 "1,3,5"
      // ...
    },
  }),
});
```

### 事件订阅前提

在飞书开放平台后台必须配置：
1. **订阅方式**：使用长连接接收事件
2. **订阅事件**：`im.message.receive_v1`
3. **订阅回调**：`card.action.trigger`

缺少任何一项，对应的事件就收不到。

---

## schema 1.0 vs 2.0 速查

| 特性 | schema 1.0 | schema 2.0 |
|------|------------|------------|
| 声明方式 | 不需要声明（默认） | 必须加 `"schema": "2.0"` |
| `action` 标签 | ✅ 支持 | ❌ 报错 200861 |
| `form` 容器 | ❌ 不支持 | ✅ 支持 |
| `checker` 勾选 | ❌ 不支持 | ✅ 支持 |
| 按钮跳转 | `multi_url` | `behaviors: [{type: "open_url"}]` |
| 表单提交 | ❌ 不支持 | `form_action_type: "submit"` |
| 卡片更新 | 有限 | `config.update_multi: true` |

**选择原则**：
- 只需要展示 + 跳转按钮 → **schema 1.0**
- 需要 form / checker / 表单提交 → **schema 2.0**

---

## 常见错误及解决

| 错误码 | 错误信息 | 原因 | 解决 |
|--------|----------|------|------|
| 200861 | `action tag not support` | schema 2.0 中使用了 action 标签 | 改用 behaviors 或切回 1.0 |
| 200672 | `checker behaviors conflict` | form 内的 checker 配了 behaviors | 删除 checker 的 behaviors |
| 230001 | `invalid card` | JSON 格式错误 | 检查 JSON 是否合法 |
| 99991663 | `msg_type not match` | content 不是字符串化的 JSON | 用 JSON.stringify() 包装 |
| 230013 | `form element error` | form 内元素配置错误 | 检查 form 内每个元素的必填字段 |
| 回调超时 | 无错误码，但卡片无响应 | 回调处理超过3秒 | 重操作用异步，先返回 toast |

---

## 发送纯文本消息（备用）

有时候不需要复杂卡片，发一条纯文本就够了：

```typescript
async function sendText(chatId: string, text: string) {
  await client.im.v1.message.create({
    params: { receive_id_type: "chat_id" },
    data: {
      receive_id: chatId,
      msg_type: "text",
      content: JSON.stringify({ text }),
    },
  });
}

// 使用
await sendText("oc_xxxxx", "✅ 【第1篇】排版完成 (mint-fresh)");
await sendText("oc_xxxxx", "📤 【第1篇】已推送到公众号草稿箱");
```

> 注意：text 消息的 content 也需要 JSON.stringify，格式为 `{"text":"消息内容"}`。
