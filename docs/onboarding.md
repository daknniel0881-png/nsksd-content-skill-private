# 新手引导：首次配置指南

> 本文档面向首次使用日生研内容创作Skill的团队成员，手把手引导你完成飞书机器人和微信公众号的配置。
> 预计耗时：15-20分钟。

---

## 总览：你需要配置两样东西

| # | 配置项 | 用途 | 需要的凭据 |
|---|--------|------|------------|
| 1 | **飞书自建应用（机器人）** | 接收选题卡片、发送通知、创建云文档 | App ID + App Secret + 用户 Open ID |
| 2 | **微信公众号开放平台** | 推送文章到公众号草稿箱 | App ID + App Secret + IP白名单 |

配好这两样，Skill 就能完整运行了。

---

## 第一部分：飞书机器人配置

### Step 1：创建飞书自建应用

1. 打开浏览器，访问 **飞书开放平台**：https://open.feishu.cn/app
2. 点击右上角 **「创建应用」**
3. 选择 **「企业自建应用」**
4. 填写：
   - 应用名称：`日生研内容助手`（或你喜欢的名字）
   - 应用描述：`日生研NSKSD内容创作自动化`
   - 应用图标：随意选一个
5. 点击 **「创建」**

### Step 2：获取 App ID 和 App Secret

1. 创建完成后，进入应用详情页
2. 在左侧菜单找到 **「凭证与基础信息」**
3. 你会看到：
   - **App ID**：类似 `cli_a5xxxxxxxxxxxx`
   - **App Secret**：点击「显示」后可以看到，类似 `xxxxxxxxxxxxxxxxxxxxxxxx`
4. **把这两个值记下来**，后面要填到配置文件里

> ⚠️ App Secret 是敏感信息，不要发到群里或截图分享。

### Step 3：开通应用权限

在左侧菜单找到 **「权限管理」**，搜索并开通以下权限：

| 权限名称 | 权限标识 | 用途 |
|----------|----------|------|
| 以应用身份发送消息 | `im:message:send_as_bot` | 发送选题卡片和通知 |
| 获取与发送单聊、群组消息 | `im:message` | 接收用户的回复消息 |
| 查看、评论、编辑和管理云文档 | `docx:document` | 创建选题方案云文档 |
| 查看、评论、编辑和管理云空间文件 | `drive:drive` | 管理云文档权限 |

操作方法：
1. 点击 **「权限管理」** → **「API权限」**
2. 在搜索框搜索上面的权限标识（如 `im:message:send_as_bot`）
3. 找到后点击 **「开通」**
4. 四个权限都开通完成

### Step 4：配置事件订阅（长连接模式）

这一步让机器人能接收用户在卡片上的操作（比如勾选选题后点提交）。

1. 在左侧菜单找到 **「事件与回调」**
2. 点击 **「事件配置」**
3. 在 **「订阅方式」** 中选择 **「使用长连接接收事件」**

   > 为什么选长连接？因为不需要你有公网服务器，本地电脑就能接收事件。

4. 点击 **「添加事件」**，搜索并添加以下两个事件：
   - `im.message.receive_v1` — 接收消息事件（用户回复文字时触发）
   - `card.action.trigger` — 卡片回调事件（用户在卡片上点按钮时触发）

5. 保存配置

### Step 5：启用机器人能力

1. 在左侧菜单找到 **「应用能力」** → **「机器人」**
2. 点击 **「启用机器人」**
3. 机器人描述可以写：`日生研NSKSD内容创作助手`

### Step 6：发布应用版本

1. 在左侧菜单找到 **「版本管理与发布」**
2. 点击 **「创建版本」**
3. 填写版本号（如 `1.0.0`）和更新说明
4. 点击 **「保存」** → **「申请发布」**
5. 如果你是管理员，可以直接审批通过
6. 如果不是管理员，需要企业管理员在飞书管理后台审批

> 发布后，机器人才能在飞书中搜索到和使用。

### Step 7：获取用户 Open ID

Open ID 是机器人给你发消息时用来定位"发给谁"的标识。

**方法一：让机器人自己告诉你**
1. 在飞书中搜索你刚创建的机器人，发一条消息（如"你好"）
2. 查看监听服务的日志，会输出发送者的 `open_id`

**方法二：通过API查询**
```bash
# 替换为你的 App ID 和 App Secret
curl -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"cli_a5xxxx","app_secret":"xxxxx"}'

# 用返回的 tenant_access_token 查询用户
curl 'https://open.feishu.cn/open-apis/contact/v3/users/find?user_id_type=open_id&mobile=+86你的手机号' \
  -H 'Authorization: Bearer t-xxxxx'
```

**方法三：飞书管理后台**
1. 访问 https://admin.feishu.cn
2. 找到目标用户，查看详情中的 Open ID

把获取到的 Open ID 记下来（格式类似 `ou_xxxxxxxxxxxxxxxx`）。

### 飞书配置完成检查清单

- [ ] App ID 已获取
- [ ] App Secret 已获取
- [ ] 4个权限已开通（im:message:send_as_bot, im:message, docx:document, drive:drive）
- [ ] 事件订阅已配置（长连接模式 + im.message.receive_v1 + card.action.trigger）
- [ ] 机器人能力已启用
- [ ] 应用版本已发布
- [ ] 目标用户 Open ID 已获取

---

## 第二部分：微信公众号配置

### Step 1：获取 App ID 和 App Secret

1. 打开浏览器，访问 **微信公众平台**：https://mp.weixin.qq.com
2. 用管理员微信扫码登录
3. 在左侧菜单找到 **「设置与开发」** → **「基本配置」**
4. 你会看到：
   - **开发者ID（AppID）**：类似 `wx0a5184f2xxxxxxxx`
   - **开发者密码（AppSecret）**：点击「重置」可以获取新的密码

   > ⚠️ AppSecret 重置后旧的立即失效。如果其他地方在用旧的 AppSecret，需要同步更新。
   > ⚠️ AppSecret 只显示一次，重置后请立即复制保存。

5. 把 AppID 和 AppSecret 记下来

### Step 2：配置 IP 白名单（关键！）

> 这是最容易出错的一步。如果不配置 IP 白名单，调用微信API时会报错 `errcode=40164`（IP不在白名单中）。

1. 在同一个页面（「设置与开发」→「基本配置」），找到 **「IP白名单」**
2. 点击 **「查看」** 或 **「修改」**

**你需要添加的 IP 地址：**

首先确认你的出口 IP：
```bash
# 在你运行脚本的电脑上执行
curl ifconfig.me
# 输出类似：38.90.16.xxx
```

然后把这个 IP 添加到白名单中。

**推荐配置方式**：
- 如果你的 IP 是固定的：只添加你的 IP，如 `38.90.16.123`
- 如果你的 IP 会变（家庭宽带/移动网络）：添加一个网段，如 `38.90.16.0/24`（覆盖 38.90.16.0 ~ 38.90.16.255）
- 如果你使用 Claude Code 的云服务，IP 可能会变，建议添加较宽的网段

**具体操作**：
1. 点击 **「修改」**
2. 在输入框中填入你的 IP 地址（每行一个）
3. 点击 **「确认修改」**
4. 微信会要求管理员扫码确认

**验证白名单是否生效**：
```bash
# 替换为你的 AppID 和 AppSecret
curl "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=你的AppID&secret=你的AppSecret"

# 成功返回：{"access_token":"xxx","expires_in":7200}
# 失败返回：{"errcode":40164,"errmsg":"invalid ip xxx, not in whitelist"}
```

如果返回 `40164` 错误，说明 IP 白名单没配对，检查错误信息中的 IP 是否已添加到白名单。

### Step 3：确认公众号类型

推送草稿箱功能需要 **已认证的服务号或订阅号**。

查看方式：在公众号后台首页，头像下方会显示类型：
- ✅ 已认证订阅号 — 可以使用
- ✅ 已认证服务号 — 可以使用
- ❌ 未认证订阅号 — 部分API可能受限

### 微信配置完成检查清单

- [ ] AppID 已获取
- [ ] AppSecret 已获取并保存
- [ ] IP 白名单已配置（已验证 `curl` 能成功获取 token）
- [ ] 公众号类型确认（已认证）

---

## 第三部分：填写配置文件

两部分凭据都拿到后，填入配置文件。

### 3.1 环境变量文件

```bash
cd ~/.claude/skills/nsksd-content/scripts/server
cp .env.example .env
```

用编辑器打开 `.env`，填入：

```env
# ====== 飞书配置 ======
LARK_APP_ID=cli_a5xxxxxxxxxxxx        # Step 1-2 获取的飞书 App ID
LARK_APP_SECRET=xxxxxxxxxxxxxxxx      # Step 1-2 获取的飞书 App Secret
TARGET_OPEN_ID=ou_xxxxxxxxxxxxxxxx    # Step 1-7 获取的用户 Open ID

# ====== 微信配置 ======
WECHAT_APP_ID=wxxxxxxxxxxx           # Step 2-1 获取的微信 AppID
WECHAT_APP_SECRET=xxxxxxxxxxxxxxxx   # Step 2-1 获取的微信 AppSecret

# ====== 路径配置 ======
SKILL_PATH=/path/to/nsksd-content    # Skill 安装的绝对路径
PORT=9800                             # HTTP管理端口（默认9800，一般不用改）
```

### 3.2 配置文件（config.json）

```bash
cd ~/.claude/skills/nsksd-content
cp config.json.example config.json
```

编辑 `config.json`：

```json
{
  "output_dir": "/tmp/wechat-format",
  "vault_root": "/path/to/your/obsidian/vault",
  "settings": {
    "default_theme": "mint-fresh",
    "auto_open_browser": false
  },
  "wechat": {
    "app_id": "wxxxxxxxxxxx",
    "app_secret": "xxxxxxxxxxxxxxxx",
    "author": "你的公众号作者名"
  }
}
```

> `wechat.author` 填写你希望在公众号文章底部显示的作者名。

### 3.3 安装依赖

```bash
# 安装服务端依赖（飞书SDK等）
cd ~/.claude/skills/nsksd-content/scripts/server
bun install

# 安装 Python 依赖（排版和发布脚本需要）
pip3 install markdown requests python-dotenv
```

---

## 第四部分：验证配置

### 4.1 验证飞书连接

```bash
cd ~/.claude/skills/nsksd-content/scripts/server
source .env && bun run index.ts
```

看到以下日志说明飞书连接成功：
```
[info]: [ "event-dispatch is ready" ]
[info]: [ "[ws]", "ws client ready" ]
[HTTP] 本地管理端口: http://localhost:9800
```

### 4.2 验证微信 API

在另一个终端窗口：
```bash
# 测试获取 access_token
curl "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=你的AppID&secret=你的AppSecret"
```

返回 `access_token` 字段说明微信配置正确。

### 4.3 验证完整流程

```bash
# 测试发送飞书卡片
curl -X POST http://localhost:9800/send-card -H 'Content-Type: application/json' -d '{}'
```

检查飞书是否收到选题卡片。

---

## 常见问题

### 飞书相关

| 问题 | 原因 | 解决 |
|------|------|------|
| WSClient 连接失败 | 未选择"长连接"订阅方式 | 飞书后台 → 事件与回调 → 改为长连接 |
| 发送消息报权限错误 | 权限未开通或未发布版本 | 检查4个权限 + 发布新版本 |
| 卡片点击无反应 | 未订阅 card.action.trigger 事件 | 飞书后台添加该事件 |
| Open ID 找不到 | 用户未和机器人有过交互 | 先在飞书中给机器人发一条消息 |

### 微信相关

| 问题 | 原因 | 解决 |
|------|------|------|
| `errcode=40164` | IP 不在白名单 | 添加当前出口IP到白名单 |
| `errcode=40001` | AppSecret 错误 | 重新获取 AppSecret |
| `errcode=40125` | AppSecret 格式不对 | 检查是否复制完整，有无多余空格 |
| `errcode=48001` | API权限不足 | 需要已认证的公众号 |
| 封面图上传失败 | 图片格式不支持 | 使用 jpg/png，大小 < 2MB |
| 草稿推送失败 | HTML 格式问题 | 检查是否包含微信不支持的标签 |

---

## 下一步

配置完成后：
1. 重启 Claude Code（让 Skill 生效）
2. 输入 `/nsksd` 开始使用
3. 遇到问题查看 [docs/setup.md](setup.md) 或本文档的常见问题
