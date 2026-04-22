# Windows 排障说明书（V9.8 新增）

> 日生研 NSKSD Skill 在 Windows 11 上的完整踩坑记录 + 修法。
> 源自 2026-04-21~22 客户端测试报告 `nska-windows-test-report.md`。

## 快速索引

| 症状 | 跳转 |
|------|------|
| Claude Code Bash 工具报错「not found」 | [#1 Bash 工具路径坑](#1-bash-工具路径坑) |
| 飞书消息中文变乱码 `���` | [#2 编码乱码](#2-中文消息乱码) |
| `daily-topics.ps1` 找不到 | [#3 定时脚本缺失](#3-定时任务-daily-topicsps1-找不到) |
| 飞书开放平台 404 | [#4 开放平台 URL 错误](#4-飞书开放平台-url) |
| `LARK_APP_ID 未设置` | [#5 凭证未注入](#5-lark_app_id--lark_app_secret-未设置) |
| 多选卡点了没反应 | [#6 回调监听器未运行](#6-多选卡回调不触发) |
| 安全软件误报 PS1 为病毒 | [#7 安全软件白名单](#7-安全软件误报) |
| 虚拟环境 `bad interpreter` | [#8 venv 路径失效](#8-venv-坏了) |

---

## 1. Bash 工具路径坑

### 症状

```
Skipping command-line '"C:\Program Files\Git\bin\..\usr\bin\bash.exe"'
('C:\Program Files\Git\bin\..\usr\bin\bash.exe' not found)
```

### 根因

Claude Code 内部硬编码 `Git\bin\..\usr\bin\bash.exe`，该路径在 Git for Windows 默认安装下**不存在**。手动创建 `usr\bin\bash.exe` 会触发 Claude Code 的「智能路径适配」，导致每次重启基础路径再往下跳一层，形成 `usr\usr\bin\` → `usr\usr\usr\bin\` 的无限循环。

### 唯一有效修法（已验证 2026-04-22）

**重新安装 Git for Windows**：

1. 访问 <https://git-scm.com/download/win>
2. 下载最新版安装程序
3. 安装时**勾选 "Git Bash Here"** 和 "MinGit" 组件
4. 安装完成后重启 Claude Code
5. 测试：`bash --version` 在 Claude Code 内应能跑通

### 什么不要做

- ❌ 手动 `Copy-Item` bash.exe 到 `usr\bin`（会触发无限循环）
- ❌ 创建符号链接（同样会被识别）
- ❌ 反复重启 Claude Code 希望自愈

### Skill 侧如何绕开

Skill 的 Windows 版本**不依赖 Bash 工具运行**——定时入口走 PowerShell（`scripts\daily-topics.ps1`），监听器走批处理（`run_listener_win.bat`），所有跨平台逻辑通过 Python 脚本承接。

---

## 2. 中文消息乱码

### 症状

飞书客户端收到的消息显示为 `NSKSD Skill ���� - ��Ϣ���ͳɹ���`

### 根因三件套

1. Windows 控制台默认 `chcp 936`（GBK），Python stdout/stderr 继承 GBK
2. `curl` 在 Git Bash 下传中文 JSON 时 `Content-Type` 未声明 charset
3. 文件读取未显式指定 `encoding="utf-8"`

### V9.8 修法（已内置）

- `scripts/daily-topics.ps1` 开头强制：

  ```powershell
  $OutputEncoding = [System.Text.Encoding]::UTF8
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  $env:PYTHONIOENCODING = 'utf-8'
  $env:PYTHONUTF8 = '1'
  ```

- `scripts/interactive/send_notify.py` 开头：

  ```python
  if sys.platform == "win32":
      sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
      sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
  ```

- 所有 HTTP 请求固定 `Content-Type: application/json; charset=utf-8` + `json.dumps(..., ensure_ascii=False).encode('utf-8')`

### 如果仍然乱码

手动在 PowerShell 里跑：

```powershell
chcp 65001
$env:PYTHONIOENCODING = 'utf-8'
python scripts\interactive\send_notify.py --open-id ou_xxx --kind all_done --count 1
```

---

## 3. 定时任务 `daily-topics.ps1` 找不到

### 症状

```
❌ 找不到入口脚本：C:\Users\XXX\.claude\skills\nsksd-content\scripts\daily-topics.ps1
```

### 根因

V9.7 之前仓库只给了 macOS 版 `run_nsksd_daily.sh`，Windows 定时任务入口缺失。

### V9.8 修法

`scripts/daily-topics.ps1` 已入仓。安装后直接：

```powershell
# 注册定时任务（每日 10:00）
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 或单独注册
schtasks /Create /SC DAILY /ST 10:00 /TN "NSKSD-Daily-Topics" ^
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\.claude\skills\nsksd-content\scripts\daily-topics.ps1" /F

# 手动测试
schtasks /Run /TN "NSKSD-Daily-Topics"

# 查看状态
schtasks /Query /TN "NSKSD-Daily-Topics" /V /FO LIST
```

---

## 4. 飞书开放平台 URL

| 错误 | 正确（V9.8 已修正） |
|------|----|
| `https://open.feishu.cn/app` | `https://open.feishu.cn/page/launcher?from=backend_oneclick` |

旧地址会跳 404 或落到开发者中心首页，找不到自建应用入口。

---

## 5. `LARK_APP_ID` / `LARK_APP_SECRET` 未设置

### 症状

```
RuntimeError: LARK_APP_ID / LARK_APP_SECRET 未设置
```

### 推荐修法：一次交互，终身受用

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_cli.ps1
```

它会：

1. 打开 `setup_cli.py` 交互引导
2. 收集 App ID / App Secret / open_id / chat_id
3. 写入 `%USERPROFILE%\.nsksd-content\config.json`
4. 自动设置文件权限

之后 `daily-topics.ps1` / `run_listener_win.bat` / `send_notify.py` 都能自动读。

### 手动 fallback（不推荐）

编辑 `scripts\.env`：

```ini
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
TARGET_OPEN_ID=ou_xxx
TARGET_CHAT_ID=oc_xxx
```

---

## 6. 多选卡回调不触发

### 症状

- 点「提交」后飞书客户端显示「已收到」
- 但原卡片不变灰，也没有「正在撰写」通知卡

### 根因

回调需要 **`lark_ws_listener.py` WebSocket 长连接进程持续运行**。测试报告里确认监听器没起来。

### 修法

```powershell
cd scripts\interactive
.\run_listener_win.bat start       # 启动（幂等）
.\run_listener_win.bat status      # 查看状态
.\run_listener_win.bat logs        # 看日志
.\run_listener_win.bat restart     # 重启
```

V9.8 的 `run_listener_win.bat` 会**自动从 config.json 读凭证注入环境变量**，不需要手写 `start_listener.py` 包装脚本。

### 飞书开放平台权限必配

打开 <https://open.feishu.cn/page/launcher?from=backend_oneclick> 找到你的应用：

- **权限管理**：`im:message` + `im:message:send_as_bot` + `im:chat`
- **事件订阅**：开启 `card.action.trigger`（卡片交互）+ `im.message.receive_v1`
- **事件订阅模式**：选 WebSocket（本 Skill 走长连接，不走 HTTP 回调）

---

## 7. 安全软件误报

### 症状

Windows Defender / 360 / 火绒把 `daily-topics.ps1` 识别为蠕虫，导致 `schtasks` 执行时被拦截。

### 修法（按推荐度排序）

#### A. 白名单（最简单）

把以下路径加到安全软件白名单：

```
%USERPROFILE%\.claude\skills\nsksd-content\scripts\
```

#### B. PS2EXE 打包

```powershell
Install-Module -Name ps2exe -Scope CurrentUser -Force
Invoke-PS2EXE -InputFile scripts\daily-topics.ps1 -OutputFile scripts\daily-topics.exe
```

然后把 schtasks 的 `/TR` 改为 `.exe` 路径。

#### C. 数字签名（企业部署推荐）

需要一张代码签名证书，成本较高，个人部署不推荐。

---

## 8. venv 坏了

### 症状

```
.venv/bin/python: /Users/suze/...: bad interpreter
ModuleNotFoundError: No module named 'lark_oapi'
```

### 根因

`scripts\interactive\.venv\` 是在另一台机器（Mac / 其他 Windows 账号）创建的，路径硬编码失效。

### 修法

V9.8 的 `run_listener_win.bat start` 会自动校验 venv 有效性、失效就重建、缺依赖就 `pip install lark-oapi`。如果还想手动清理：

```powershell
cd scripts\interactive
Remove-Item -Recurse -Force .venv
.\run_listener_win.bat start
```

---

## 9. 完整 Windows 首次安装 Checklist

```powershell
# 1. 安装前置依赖
# - Python 3.8+     → https://www.python.org/downloads/
# - Node.js 18+     → https://nodejs.org/
# - Git for Windows → https://git-scm.com/download/win  (勾选 Git Bash Here)
# - Claude Code     → https://code.anthropic.com/

# 2. 克隆仓库
git clone https://github.com/daknniel0881-png/nsksd-content-skill-private.git %USERPROFILE%\.claude\skills\nsksd-content
cd %USERPROFILE%\.claude\skills\nsksd-content

# 3. 跑 setup（依赖检查 + 定时任务 + 飞书 CLI 授权）
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 4. 配置凭证
powershell -ExecutionPolicy Bypass -File scripts\setup_cli.ps1

# 5. 启动监听器（后台跑，别关窗口）
cd scripts\interactive
.\run_listener_win.bat start

# 6. 手动触发一次测试
cd ..
powershell -ExecutionPolicy Bypass -File scripts\daily-topics.ps1

# 7. 验收
#   - 飞书收到选题多选卡（中文正常）
#   - 勾选后原卡片变灰
#   - 收到「正在撰写」黄色通知卡
```

---

## 10. 遇到新坑怎么办

1. 先翻本文件
2. 翻 `docs/playbooks/README.md` 总索引
3. 把报错原文 + 修法写到本文件末尾（Append-only，不删旧记录）
4. 提交时 commit message 前缀 `docs(win-trouble)`

---

## 版本历史

- **V9.8**（2026-04-22）：首版，整合 14 条 Windows 踩坑
- 来源：`~/Downloads/nska-windows-test-report.md` 整晚测试产物
