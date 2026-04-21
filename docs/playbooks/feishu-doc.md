# Playbook：飞书云文档保底

> 场景：公众号凭证缺失或推送失败时，自动将文章内容创建为飞书云文档，并推送链接给用户。

---

## 何时触发保底

| 情况 | 触发条件 |
|------|----------|
| 凭证缺失 | `~/.nsksd-content/config.json` 中 `wechat.app_id` 或 `wechat.app_secret` 为空/REPLACE_ME |
| 推送失败 | `nsksd_publish.py` 返回 exit code 4 |
| 手动触发 | 运行时加 `--feishu-fallback` 参数 |

保底不是降级，而是**确保内容不丢失**。运营人员可以从飞书云文档复制内容，手动发布到公众号。

---

## 步骤

### 1. 确认飞书凭证

```bash
python3 scripts/setup_cli.py
# 确认 lark.app_id 和 lark.app_secret 已填写
```

### 2. lark-cli 创建云文档

```bash
# 语法
lark-cli docs +create \
  --title "文章标题 · NSKSD $(date +%Y-%m-%d)" \
  --markdown @/tmp/article.md

# 返回值包含 doc_token，格式如：
# {"doc_token": "doccnXXXXXX", "url": "https://..."}
```

### 3. 获取 doc_token

```bash
# lark-cli 创建后的输出里提取 doc_token
DOC_RESULT=$(lark-cli docs +create --title "..." --markdown @article.md)
DOC_TOKEN=$(echo "$DOC_RESULT" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['doc_token'])")
DOC_URL=$(echo "$DOC_RESULT" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['url'])")
```

### 4. 开放权限给群聊

```bash
# 给 chat_id（群）开可读权限，不给个人
lark-cli docs +permission \
  --doc-token "$DOC_TOKEN" \
  --member-type "chat" \
  --member-id "$CUSTOMER_OPEN_CHAT_ID" \
  --perm "view"
```

**注意：权限给 chat_id 不给 user_id**，这样群里所有人都能看，不需要逐个开权限。

### 5. 推送链接到飞书 IM

```bash
lark-cli im +messages-send \
  --as bot \
  --user-id "$TARGET_OPEN_ID" \
  --markdown "**文章已保存到飞书云文档**\n\n标题：$ARTICLE_TITLE\n链接：$DOC_URL\n\n公众号凭证缺失，请手动复制内容发布。"
```

---

## Markdown 格式规则

飞书云文档对 Markdown 有以下要求：

| 规则 | 说明 |
|------|------|
| 图片语法 | `![alt](url)` 标准格式，宽度由飞书自动处理 |
| 标题 | `#` `##` `###` 均支持 |
| 表格 | 标准 GFM 表格 |
| 代码块 | ` ``` ` 包裹，支持语言标注 |
| 特殊字符 | 不要用 HTML 标签，lark-cli 不会渲染 |
| 图片宽度 | 不需要手动设置，飞书自适应 |

**注意：图片 width=auto 铁律** — 从 HTML 转 Markdown 时，不要带 width 属性，让飞书自己处理。

---

## 参数与字段

| 字段 | 来源 | 说明 |
|------|------|------|
| `doc_token` | lark-cli 创建返回 | 文档唯一标识符 |
| `app_id` | `~/.nsksd-content/config.json` → `lark.app_id` | 机器人应用 ID |
| `app_secret` | `~/.nsksd-content/config.json` → `lark.app_secret` | 机器人应用密钥 |
| `chat_id` | `~/.nsksd-content/config.json` → `lark.customer_open_chat_id` | 客户群 chat_id |
| `target_open_id` | `~/.nsksd-content/config.json` → `lark.target_open_id` | 推送通知的个人 open_id |

---

## 常见错误

### lark-cli 命令找不到

```bash
# 检查是否安装
which lark-cli || echo "未安装"

# 安装
bun install -g @larksuiteoapi/lark-cli
# 或
npm install -g @larksuiteoapi/lark-cli

# 配置凭证
lark-cli config set --app-id "cli_xxx" --app-secret "xxx"
```

### 权限不足（403 或 permission_denied）

**检查：**
1. 机器人应用是否开启了 `docs:doc:create` 权限
2. 在飞书开放平台 → 应用 → 权限管理 → 搜索"云文档"，确认已申请并发布

### 文档创建后链接失效

**原因**：创建时机器人没有发布或权限审核未通过。

**处理**：在飞书开放平台 → 应用 → 版本管理，确认应用已发布到目标企业。

---

## 验证方法

```bash
# 手动测试保底流程
python3 scripts/nsksd_publish.py \
  --html /tmp/test.html \
  --title "测试文章" \
  --mock-wechat-fail  # 模拟公众号推送失败，触发飞书保底
```

检查：
1. 飞书 IM 是否收到通知
2. 通知里的链接是否可以打开
3. 文档内容是否完整

---

## 回查兜底

飞书保底也失败时：
1. 检查飞书凭证是否正确（`python3 scripts/setup_cli.py`）
2. 检查 lark-cli 是否有效（`lark-cli --version`）
3. 内容已保存到 `/tmp/nsksd-article-<session>.md`，可手动上传
4. [待曲率确认] 如果飞书保底也失败，是否需要 email 通知客户？
