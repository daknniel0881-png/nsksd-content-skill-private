# 日生研NSKSD · 自动化选题系统部署指南

> 本指南面向日生研运营团队，帮助你在5分钟内完成自动化选题+写稿系统的部署。

## 系统架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  定时任务    │ →   │ Claude CLI   │ →   │  飞书卡片    │
│ (每日9:00)  │     │ 生成10个选题  │     │ 展示选题列表  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │ 用户回复编号
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  飞书推送    │ ←   │ Claude CLI   │ ←   │ WSClient    │
│ 完整文案     │     │ 生成文案      │     │ 长连接监听   │
└─────────────┘     └──────────────┘     └─────────────┘
```

**核心优势**：
- 不需要公网服务器（使用飞书SDK WebSocket长连接）
- 不需要内网穿透工具
- 本地运行即可，零运维成本

## 前置要求

1. **Claude Code**（已安装并登录）
2. **Bun**（JavaScript运行时）：`curl -fsSL https://bun.sh/install | bash`
3. **飞书自建应用**（已有五竹机器人可直接使用）

## 一、飞书应用配置（首次，约3分钟）

### 1.1 开启事件订阅

1. 打开飞书开发者后台：https://open.feishu.cn/app
2. 选择你的应用（如五竹机器人）
3. 进入 **事件与回调** 页面
4. 点击 **添加事件**，搜索并添加：`im.message.receive_v1`（接收消息）
5. 在 **订阅方式** 中选择 **「使用长连接接收事件」**
6. 保存

### 1.2 确认权限

确保应用有以下权限（通常已有）：
- `im:message:send_as_bot`（发送消息）
- `im:message`（接收消息）

### 1.3 发布版本

如果有变更，需要在 **版本管理** 中创建新版本并发布。

## 二、安装Skill（约2分钟）

### 方式一：从GitHub克隆

```bash
cd ~/.claude/skills/
git clone https://github.com/daknniel0881-png/nsksd-content-skill-private.git nsksd-content
```

### 方式二：从zip解压

```bash
unzip nsksd-content-skill.zip -d ~/.claude/skills/nsksd-content
```

### 安装依赖

```bash
cd ~/.claude/skills/nsksd-content/scripts/server
bun install
```

## 三、配置环境变量

```bash
cd ~/.claude/skills/nsksd-content/scripts
cp .env.example .env
```

编辑 `.env` 文件，填入实际值：

```env
LARK_APP_ID=cli_xxxxxxxx
LARK_APP_SECRET=xxxxxxxx
TARGET_OPEN_ID=ou_xxxxxxxx
SKILL_PATH=/path/to/nsksd-content
```

## 四、启动监听服务

```bash
cd ~/.claude/skills/nsksd-content/scripts
source .env && export LARK_APP_ID LARK_APP_SECRET TARGET_OPEN_ID SKILL_PATH

# 启动WSClient长连接监听
cd server && bun run index.ts
```

看到以下日志说明启动成功：
```
[info]: [ "event-dispatch is ready" ]
[info]: [ "[ws]", "ws client ready" ]
```

## 五、发送选题卡片

在另一个终端窗口：

```bash
cd ~/.claude/skills/nsksd-content/scripts
source .env && export LARK_APP_ID LARK_APP_SECRET TARGET_OPEN_ID

# 方式1：使用已有选题文件
bun run send-topic-card.ts /path/to/topics.md

# 方式2：先生成新选题再发送
./daily-topics.sh --generate   # 生成选题
./daily-topics.sh --card       # 发送卡片
```

## 六、使用流程

1. 飞书收到选题卡片（10个选题，按S/A/B分级）
2. 直接回复数字编号选择：`1 3 5`（选第1、3、5篇）
3. 监听服务自动触发Claude CLI生成文案
4. 文案生成后自动推送到飞书

**支持的回复格式**：
- `1 3 5` — 空格分隔
- `1,3,5` — 逗号分隔
- `1、3、5` — 顿号分隔
- `选题列表` — 查看当前选题
- `帮助` — 显示帮助

## 七、设置定时任务（可选）

### Mac (Launchd)

```bash
./daily-topics.sh  # 一键启动完整流程
```

设置每日自动执行：

```bash
# 创建定时任务（每天9:00执行）
cat > ~/Library/LaunchAgents/com.nsksd.daily-topics.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nsksd.daily-topics</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd ~/.claude/skills/nsksd-content/scripts && source .env && export LARK_APP_ID LARK_APP_SECRET TARGET_OPEN_ID SKILL_PATH && ./daily-topics.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/nsksd-daily.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/nsksd-daily-error.log</string>
</dict>
</plist>
EOF

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.nsksd.daily-topics.plist
```

### Windows (Task Scheduler)

```powershell
.\daily-topics.ps1              # 一键启动完整流程
.\daily-topics.ps1 -Mode server # 只启动监听服务
```

设置每日自动执行：

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-File `"$HOME\.claude\skills\nsksd-content\scripts\daily-topics.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "NSKSD-DailyTopics" -Action $action -Trigger $trigger
```

## 八、故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| WSClient连接失败 | 飞书后台未开启长连接 | 按步骤一配置 |
| 回复数字无反应 | 未订阅im.message.receive_v1 | 飞书后台添加事件 |
| 卡片发送失败 | Token过期 | 检查APP_ID和APP_SECRET |
| Claude CLI报错 | 未登录或额度不足 | 运行`claude`确认状态 |
| 文案生成超时 | 文案较长 | 正常，每篇约2-5分钟 |
| 监听服务退出 | 终端关闭 | 用`nohup`或`screen`运行 |

## 九、文件结构

```
scripts/
├── .env.example          ← 环境变量模板
├── .env                  ← 实际配置（不提交git）
├── send-topic-card.ts    ← 发送选题卡片脚本
├── daily-topics.sh       ← Mac/Linux一键脚本
├── daily-topics.ps1      ← Windows一键脚本
└── server/
    ├── index.ts          ← WSClient长连接监听服务
    ├── package.json      ← 依赖配置
    └── node_modules/     ← 依赖包（bun install后生成）
```
