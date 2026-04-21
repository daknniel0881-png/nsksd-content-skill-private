# 飞书 CLI 自动授权指南（V9.1）

本文件说明 `scripts/setup.sh` / `setup.ps1` 的 Step 3.6 做了什么，以及手动故障恢复步骤。

## 1. 为什么要装飞书 CLI

Skill 的每日 10:00 多选卡片走 bun + 飞书 SDK 长连接推送，**本身不依赖 lark CLI**。
引入 lark CLI 的目的：

- 日常排错时能一行命令测 `lark whoami` / `lark im message send`
- 新机器首次授权不用进开发者后台点 UI，`lark login` 直接拿 token
- 后续扩展（lark-doc 交付、lark-drive 备份等）的统一入口

## 2. 自动安装（V9.1 起默认开启）

运行 `bash scripts/setup.sh`（macOS/Linux）或 `pwsh scripts/setup.ps1`（Windows）即可，脚本会：

1. 检测 `bun` 不存在 → 自动 `curl -fsSL https://bun.sh/install | bash` 并写 `~/.zshrc` PATH
2. 检测 `lark` 不存在 → 自动 `bun install -g @larksuiteoapi/lark-cli`（失败则 fallback `npm i -g`）
3. 读 `scripts/server/.env` 的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` → 自动 `lark login` 或 `lark config set`
4. 全程幂等，已装不重装

## 3. 手动命令备查

```bash
# 安装 bun
curl -fsSL https://bun.sh/install | bash

# 安装 lark CLI
bun install -g @larksuiteoapi/lark-cli
# 或
npm install -g @larksuiteoapi/lark-cli

# 授权（两种写法，用哪个取决于你安装的版本）
lark login --app-id cli_xxx --app-secret yyy
# 或
lark config set app_id cli_xxx
lark config set app_secret yyy

# 验证
lark whoami
lark im chat list --limit 5
```

## 4. 常见错误

| 现象 | 原因 | 修复 |
|------|------|------|
| `command not found: bun` | 新 shell 未加载 PATH | `source ~/.zshrc` 或重开终端 |
| `command not found: lark` | 全局 bin 未加 PATH | `export PATH="$HOME/.bun/bin:$PATH"` |
| `error 10001 invalid app_id` | `.env` 填错 APP_ID | 去 `https://open.feishu.cn/page/launcher` 核对 |
| `error 99991663 access_token expired` | token 90 天过期 | 重新 `lark login` |
| `network timeout` | 企业网络屏蔽 bun.sh | 走 npm fallback 或手动下载二进制 |

## 5. 客户品牌名硬约束

所有飞书推送文案涉及客户名一律使用 **「日生研」** 三字，严禁写成 "日升盐" / "日生盐"。
