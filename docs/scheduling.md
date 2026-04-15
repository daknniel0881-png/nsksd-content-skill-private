# 定时任务配置

> 本文档说明如何在 Mac 和 Windows 上配置每日自动选题推送。

## 定时脚本流程

`scripts/run_nsksd_daily.sh` 是每日定时任务的入口，执行以下流程：

```
STEP 1: generate_topics → Claude CLI 生成选题 → 提取 JSON
STEP 2: create_feishu_doc → 创建飞书云文档 → 写入选题详情
STEP 3: start_listener → 启动 WSClient 监听服务 → 注册选题
STEP 4: send_topic_cards → 通过监听服务 HTTP 端口发送两张卡片（清单卡 + 多选卡）
```

## Mac（LaunchAgent）

### 安装

plist 文件中的路径需要替换为你的实际路径。运行以下命令自动替换并安装：

```bash
# 在 skill 根目录执行
SKILL_PATH="$(pwd)"
sed "s|/tmp/nsksd-content-skill|$SKILL_PATH|g; s|/Users/suze|$HOME|g" \
  scripts/com.nsksd.daily-topics.plist > ~/Library/LaunchAgents/com.nsksd.daily-topics.plist

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.nsksd.daily-topics.plist
```

### 常用操作

```bash
# 手动触发（测试用）
launchctl start com.nsksd.daily-topics

# 查看状态
launchctl list | grep nsksd

# 卸载
launchctl unload ~/Library/LaunchAgents/com.nsksd.daily-topics.plist

# 查看日志
tail -f logs/daily-$(date +%Y-%m-%d).log
tail -f logs/launchd-stdout.log
```

### plist 要点

- 每天 10:00 本地时间触发
- 需要设置 PATH 环境变量（launchd 环境的 PATH 极简，找不到 claude/bun）
- `RunAtLoad: false`（仅在计划时间运行，不在系统启动时运行）
- `KeepAlive: false`（失败后不自动重启，避免循环崩溃）

### 注意事项

- macOS 休眠时 LaunchAgent 不触发。如果10点电脑在睡眠，会在唤醒后补执行
- 如果修改了 plist，需要先 unload 再 load 才能生效
- 日志文件位于 `logs/` 目录，按日期分割

## Windows（Task Scheduler）

### 安装

1. 编辑 `scripts/nsksd-daily-topics-task.xml`，修改以下路径为实际值：
   - `<WorkingDirectory>` → 你的 skill scripts 目录
   - `<Arguments>` 中的 ps1 文件路径
   - `<UserId>` → 你的 Windows SID（或删除此行使用当前用户）

2. 以管理员身份运行 PowerShell：
```powershell
schtasks /Create /TN "NSKSD\DailyTopics" /XML "C:\path\to\nsksd-daily-topics-task.xml"
```

或者在任务计划程序 GUI 中导入 XML 文件。

### 常用操作

```powershell
# 手动触发
schtasks /Run /TN "NSKSD\DailyTopics"

# 查看状态
schtasks /Query /TN "NSKSD\DailyTopics" /V

# 卸载
schtasks /Delete /TN "NSKSD\DailyTopics" /F
```

### Windows 依赖

Windows 上需要通过 WSL 或 Git Bash 运行 bash 脚本。`scripts/daily-topics.ps1` 是 PowerShell 包装脚本，内部调用 bash：

```powershell
# daily-topics.ps1 的核心逻辑
bash "$PSScriptRoot/run_nsksd_daily.sh"
```

确保 Windows 上已安装：
- WSL 或 Git Bash（用于执行 bash 脚本）
- Claude Code（需要在 PATH 中）
- Bun（需要在 PATH 中）
- Python 3（需要在 PATH 中）

## 环境变量配置

定时脚本从 `scripts/server/.env` 加载环境变量，参考 `.env.example`：

```env
LARK_APP_ID=xxx           # 飞书应用 App ID
LARK_APP_SECRET=xxx       # 飞书应用 App Secret
TARGET_OPEN_ID=xxx        # 接收卡片的用户 open_id
SKILL_PATH=/path/to/skill # Skill 根目录
PORT=9800                 # HTTP 管理端口
WECHAT_APP_ID=xxx         # 微信公众号 App ID
WECHAT_APP_SECRET=xxx     # 微信公众号 App Secret
```

> ⚠️ 不要将 `.env` 文件提交到 Git。每个用户需自行配置自己的凭据。

## 故障排查

| 问题 | 排查方法 |
|------|----------|
| 定时任务没触发 | Mac: `launchctl list \| grep nsksd`；Windows: 任务计划程序查看上次运行时间 |
| Claude CLI 找不到 | 检查 plist 中 PATH 是否包含 `/opt/homebrew/bin`（Mac）或检查 PATH 环境变量 |
| Bun 找不到 | 同上，确保 PATH 包含 bun 安装目录 |
| 飞书卡片没收到 | 查看 `logs/daily-*.log` 和 `logs/server.log` |
| 选题生成失败 | 查看 `logs/daily-*.log` 中 STEP 1 的错误信息 |
| 监听服务未启动 | `curl http://localhost:9800/health` 检查 |
