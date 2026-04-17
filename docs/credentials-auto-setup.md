# 凭据自动配置指引（Agent 专用）

> **本文档面向 AI Agent 阅读，不是给人类看的操作手册。**
> Agent 读完本文档后，应能自动完成 90% 的凭据获取和配置工作，仅在必要时向用户确认。

---

## 凭据总览

| 凭据 | 写入位置 | 自动获取方式 | 是否需要用户提供 |
|------|----------|-------------|----------------|
| 飞书 App ID | `.env` → `LARK_APP_ID` | `lark-cli config show` → `appId` | ❌ 自动获取 |
| 飞书 App Secret | `.env` → `LARK_APP_SECRET` | 从 lark-cli 配置文件读取 | ❌ 自动获取 |
| 飞书用户 Open ID | `.env` → `TARGET_OPEN_ID` | `lark-cli config show` → `users` 字段解析 | ❌ 自动获取 |
| 飞书群聊 Chat ID | `.env` → `CHAT_ID`（可选） | `lark-cli im +chat-search --query "群名"` | ⚠️ 需用户告知群名 |
| 微信 App ID | `.env` → `WECHAT_APP_ID` + `config.json` | 无 CLI 工具，需用户提供一次 | ✅ 必须用户提供 |
| 微信 App Secret | `.env` → `WECHAT_APP_SECRET` + `config.json` | 无 CLI 工具，需用户提供一次 | ✅ 必须用户提供 |
| 微信 IP 白名单 | 公众号后台手动配置 | `curl ifconfig.me` 获取当前 IP | ⚠️ 自动查 IP，人工加白名单 |
| Skill 安装路径 | `.env` → `SKILL_PATH` | Agent 自行定位 Skill 目录 | ❌ 自动获取 |

---

## 第一步：检查 lark-cli 是否可用

```bash
which lark-cli && lark-cli config show
```

### 情况A：lark-cli 已安装且已配置

输出中包含 `appId`、`appSecret`（显示 `****`）、`users` 字段 → **直接进入第二步**。

### 情况B：lark-cli 已安装但未配置

输出中 `appId` 为空 → 需要用户提供飞书 App ID 和 App Secret：

**向用户说：**
> 需要你的飞书应用凭据来完成配置。请到飞书开放平台（https://open.feishu.cn/app）找到你的自建应用，把 App ID 和 App Secret 发给我。
> 如果还没创建应用，请先创建一个企业自建应用。详见本 Skill 的 `docs/onboarding.md`。

拿到后执行：
```bash
echo "APP_SECRET" | lark-cli config init --app-id "APP_ID" --app-secret-stdin --brand feishu
```

### 情况C：lark-cli 未安装

**向用户说：**
> 需要安装 lark-cli 来自动配置飞书凭据。请运行：
> ```
> npm install -g @nicepkg/lark-cli
> ```
> 安装后我会自动完成后续配置。

---

## 第二步：自动获取飞书凭据

### 2.1 获取 App ID 和 App Secret

```bash
# 获取 App ID
lark-cli config show --jq '.appId'

# App Secret 存储在 lark-cli 配置文件中，路径通过 config show 的最后一行获取
# 配置文件路径格式：/Users/xxx/.lark-cli/config.json 或类似
# 直接读取配置文件获取明文 Secret
```

**解析方法：**
1. 执行 `lark-cli config show`
2. 输出最后一行 `Config file path: /path/to/config.json` → 读取该文件
3. 从 JSON 中提取 `appId` 和 `appSecret`

```bash
# 示例：一条命令拿到 App ID 和 App Secret
CONFIG_PATH=$(lark-cli config show 2>&1 | grep "Config file path:" | sed 's/Config file path: //')
cat "$CONFIG_PATH"
# 输出 JSON 中包含 appId 和 appSecret 明文
```

### 2.2 获取用户 Open ID

```bash
# 方法一：从 lark-cli config show 的 users 字段解析
# users 格式："用户名 (ou_xxxxxxxxxxxxxxxx)"
# 用正则提取括号内的 ou_ 开头的字符串
lark-cli config show 2>&1 | grep -oE 'ou_[a-f0-9]+'
```

```bash
# 方法二：如果 users 字段为空，通过搜索用户获取
# 需要用户告知姓名或手机号
lark-cli contact +search-user --query "用户姓名"
# 从返回的 JSON 中提取 open_id
```

```bash
# 方法三：通过 API 用手机号查询
lark-cli api GET /open-apis/contact/v3/users/batch_get_id \
  --data '{"mobiles":["手机号"]}' \
  --params '{"user_id_type":"open_id"}' \
  --as bot
```

> **注意**：不同飞书应用下，同一用户的 Open ID 不同。必须使用当前 lark-cli profile 对应的应用来获取。

### 2.3 获取 Chat ID（可选，群聊场景）

```bash
# 搜索群聊
lark-cli im +chat-search --query "群聊名称关键词" --as bot

# 从返回结果中提取 chat_id（格式：oc_xxxxxxxx）
```

> 如果用户没有提到群聊需求，跳过此步。默认通过 Open ID 发私聊。

---

## 第三步：获取微信凭据

微信公众平台没有 CLI 工具，必须用户提供一次。

### 3.1 检查是否已有微信凭据

```bash
# 检查 config.json 中是否已配置
cat ~/.claude/skills/nsksd-content/config.json | grep -E "app_id|app_secret" | grep -v "YOUR_"
```

如果输出非空且不是占位符 → 微信凭据已配置，跳过。

### 3.2 需要用户提供时

**向用户说：**
> 微信公众号的凭据需要你提供一次（之后就不用了）：
> 1. 打开 https://mp.weixin.qq.com → 设置与开发 → 基本配置
> 2. 把 **AppID** 和 **AppSecret** 发给我
> 3. 顺便告诉我公众号的**作者名**（显示在文章底部的名字）

### 3.3 自动配置 IP 白名单提醒

```bash
# 自动获取当前出口 IP
curl -s ifconfig.me
```

**向用户说：**
> 你的当前出口 IP 是 `X.X.X.X`，需要添加到微信公众号的 IP 白名单中：
> 公众号后台 → 设置与开发 → 基本配置 → IP白名单 → 添加 `X.X.X.X`
> （这一步必须在微信后台手动操作，我没法帮你点）

---

## 第四步：自动写入配置文件

拿到所有凭据后，Agent 自动写入两个配置文件：

### 4.1 写入 .env

```bash
SKILL_DIR="$HOME/.claude/skills/nsksd-content"
ENV_FILE="$SKILL_DIR/scripts/server/.env"

cat > "$ENV_FILE" << 'ENVEOF'
# 飞书应用凭据（自动配置，勿手动修改）
LARK_APP_ID=${获取到的飞书AppID}
LARK_APP_SECRET=${获取到的飞书AppSecret}
TARGET_OPEN_ID=${获取到的OpenID}
# CHAT_ID=${如果有群聊ID则填入}

SKILL_PATH=${Skill安装路径}
PORT=9800

# 微信公众号凭据
WECHAT_APP_ID=${用户提供的微信AppID}
WECHAT_APP_SECRET=${用户提供的微信AppSecret}
ENVEOF
```

### 4.2 写入 config.json

```bash
CONFIG_FILE="$SKILL_DIR/config.json"

cat > "$CONFIG_FILE" << 'CFGEOF'
{
  "output_dir": "/tmp/wechat-format",
  "vault_root": "/path/to/obsidian/vault",
  "settings": {
    "default_theme": "mint-fresh",
    "auto_open_browser": false
  },
  "wechat": {
    "app_id": "${用户提供的微信AppID}",
    "app_secret": "${用户提供的微信AppSecret}",
    "author": "${用户提供的作者名}"
  }
}
CFGEOF
```

### 4.3 安装依赖

```bash
cd "$SKILL_DIR/scripts/server" && bun install
pip3 install markdown requests python-dotenv 2>/dev/null || pip install markdown requests python-dotenv
```

---

## 第五步：验证配置

### 5.1 验证飞书

```bash
# 尝试发一条测试消息
lark-cli im +messages-send --user-id "${TARGET_OPEN_ID}" --text "🔧 日生研内容创作 Skill 配置成功！" --as bot
```

成功 → 飞书配置 OK。
失败 → 检查 App ID/Secret 是否正确、应用是否已发布、权限是否已开通。

### 5.2 验证微信

```bash
curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${WECHAT_APP_ID}&secret=${WECHAT_APP_SECRET}"
```

返回 `access_token` → 微信配置 OK。
返回 `errcode=40164` → IP 白名单未配置。
返回 `errcode=40001` → AppSecret 错误。

---

## 完整自动配置流程（Agent 执行清单）

```
1. which lark-cli → 检查是否安装
2. lark-cli config show → 检查是否已配置
3. 从 lark-cli 配置文件提取 appId + appSecret
4. 从 lark-cli config show 输出解析 open_id
5. （可选）lark-cli im +chat-search 获取 chat_id
6. 检查 config.json 是否已有微信凭据
7. 如果没有 → 问用户要微信 AppID + AppSecret + 作者名
8. curl ifconfig.me → 提醒用户加 IP 白名单
9. 写入 .env 和 config.json
10. bun install + pip install
11. 发测试消息验证飞书
12. curl 验证微信 token
13. 全部通过 → 配置完成
```

---

## 故障排查

| 症状 | 原因 | Agent 应执行 |
|------|------|-------------|
| `lark-cli config show` 无 users | 用户未和机器人交互过 | 让用户在飞书中给机器人发一条消息，然后重新 `lark-cli config show` |
| Open ID 为空 | 应用未发布 | 提醒用户到飞书开放平台发布应用版本 |
| `errcode=40164` | 微信 IP 白名单 | `curl ifconfig.me` 获取 IP，提醒用户添加 |
| `errcode=40001` | 微信 AppSecret 错误 | 让用户重新提供 AppSecret |
| `bun: command not found` | 未安装 bun | `curl -fsSL https://bun.sh/install | bash` |
| `pip3: No module named requests` | Python 依赖缺失 | `pip3 install markdown requests python-dotenv` |
| 飞书发消息失败 | 权限未开通 | 提醒用户到飞书后台开通 `im:message:send_as_bot` 等权限 |
