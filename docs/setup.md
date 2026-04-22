# 首次安装配置指南

> 本文档指导新用户从零开始配置日生研NSKSD内容创作Skill。
>
> **首次使用？** 强烈建议先阅读 [新手引导（onboarding.md）](onboarding.md)，手把手教你配置飞书机器人和微信公众号。

## 前置依赖

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| **Claude Code** | AI写稿引擎 | [docs.anthropic.com/claude-code](https://docs.anthropic.com/claude-code) |
| **Bun** | 服务端运行时 | `curl -fsSL https://bun.sh/install \| bash` |
| **Python 3** | 排版和发布脚本 | `brew install python3` (Mac) 或 [python.org](https://python.org) |
| **markdown** (Python包) | Markdown转HTML | `pip3 install markdown` |
| **requests** (Python包) | HTTP请求 | `pip3 install requests` |
| **python-dotenv** (Python包) | 环境变量加载 | `pip3 install python-dotenv` |
| **google-genai** (Python包,可选) | AI配图 | `pip3 install google-genai pillow` |

## 快速安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/nsksd-content-skill-private.git
cd nsksd-content-skill

# 2. 运行安装脚本（自动检查依赖、创建配置文件、安装 Node 包）
bash scripts/setup.sh

# 3. 编辑配置文件（填入你的凭据）
vim scripts/server/.env
vim config.json
```

## 手动配置

### Step 1: 获取飞书应用凭据

1. 前往 [飞书开放平台](https://open.feishu.cn)，创建企业自建应用
2. 获取 `App ID` 和 `App Secret`
3. 开通以下权限：
   - `im:message:send_as_bot` — 发送消息
   - `docx:document` — 创建文档
   - `drive:drive` — 文件管理
4. 在「事件与回调」中配置：
   - 订阅方式：**使用长连接接收事件/回调**
   - 订阅事件：`im.message.receive_v1`
   - 订阅回调：`card.action.trigger`
5. 获取目标用户的 `open_id`：
   ```bash
   lark-cli contact +get-user --as user --jq '.data.user.open_id'
   ```
   未登录时先运行 `lark-cli auth login --as user`

### Step 2: 获取微信公众号凭据

1. 前往 [微信公众平台](https://mp.weixin.qq.com)
2. 在「设置与开发 → 基本配置」中获取 `AppID` 和 `AppSecret`
3. 在「设置与开发 → 基本配置 → IP白名单」中添加你的服务器IP

### Step 3: 创建环境变量文件

```bash
# 从模板创建
cp scripts/server/.env.example scripts/server/.env

# 编辑填入真实凭据
vim scripts/server/.env
```

`.env` 文件内容：
```env
LARK_APP_ID=cli_xxxxxxxxxx        # Step 1 获取的飞书 App ID
LARK_APP_SECRET=xxxxxxxxxx        # Step 1 获取的飞书 App Secret
TARGET_OPEN_ID=ou_xxxxxxxxxx      # Step 1 获取的用户 open_id
SKILL_PATH=/path/to/nsksd-content-skill  # Skill 安装目录（绝对路径）
PORT=9800                          # HTTP管理端口（默认9800）
WECHAT_APP_ID=wxxxxxxxxxxx        # Step 2 获取的微信 AppID
WECHAT_APP_SECRET=xxxxxxxxxx      # Step 2 获取的微信 AppSecret
```

### Step 4: 创建配置文件

```bash
cp config.json.example config.json
vim config.json
```

修改 `wechat` 部分：
```json
{
  "wechat": {
    "app_id": "wxxxxxxxxxxx",
    "app_secret": "xxxxxxxxxx",
    "author": "你的公众号作者名"
  }
}
```

### Step 5: 安装服务端依赖

```bash
cd scripts/server
bun install
cd ../..
```

### Step 6: 验证安装

```bash
# 启动服务
cd scripts/server && source .env && bun run index.ts

# 另开终端，检查健康状态
curl http://localhost:9800/health
# 应返回: {"status":"ok","version":"v2",...}

# 测试发送卡片
curl -X POST http://localhost:9800/send-summary-card -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:9800/send-card -H 'Content-Type: application/json' -d '{}'
```

### Step 7: 配置定时任务（可选）

见 [docs/scheduling.md](scheduling.md) 配置每日自动推送。

## 目录结构

```
nsksd-content-skill/
├── SKILL.md                    # Skill主文件（AI读取的内容创作规范）
├── config.json                 # 配置文件（.gitignore，需手动创建）
├── config.json.example         # 配置模板
├── docs/                       # 详细文档
│   ├── setup.md                # 本文件
│   ├── formatting.md           # 排版与发布
│   ├── feishu-cards.md         # 飞书卡片系统
│   └── scheduling.md           # 定时任务
├── knowledge/                  # 知识库原文（77份）
│   ├── 核心文档/               # 企业介绍、百问百答、专家建议等
│   ├── 2025新闻/               # 2025-2026年央媒报道
│   └── 2025之前/               # 历史新闻
├── references/                 # 精华提炼（快速查阅）
│   ├── knowledge-base.md       # 知识库核心素材
│   ├── topic-library.md        # 选题库+标题公式
│   ├── compliance.md           # 合规红线
│   └── compliance-checklist.md # 20项合规检查清单
├── themes/                     # 31个排版主题（JSON格式）
├── templates/                  # HTML模板（preview.html, gallery.html）
├── assets/                     # 静态资源（默认封面图等）
├── scripts/
│   ├── setup.sh                # 安装配置脚本
│   ├── run_nsksd_daily.sh      # 每日定时脚本
│   ├── com.nsksd.daily-topics.plist  # Mac定时任务
│   ├── nsksd-daily-topics-task.xml   # Windows定时任务
│   ├── format/
│   │   ├── format.py           # Markdown → HTML排版
│   │   └── publish.py          # HTML → 公众号草稿箱
│   └── server/
│       ├── index.ts            # WSClient长连接服务
│       ├── .env.example        # 环境变量模板
│       └── package.json        # Node依赖
└── logs/                       # 运行日志（.gitignore）
```

## 安全提醒

- `.env` 和 `config.json` 包含真实API密钥，**已在 .gitignore 中排除**，不会被提交到Git
- 如果你不小心提交了包含密钥的文件，请立即轮换（rotate）所有泄露的凭据
- 飞书应用建议只开通必要的最小权限
