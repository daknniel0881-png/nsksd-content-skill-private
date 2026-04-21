#!/bin/bash
# ============================================================
# 日生研NSKSD · 首次安装配置脚本
#
# 用法：cd nsksd-content-skill && bash scripts/setup.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  日生研NSKSD · 内容创作Skill 安装配置"
echo "============================================"
echo ""

# ---- Step 1: 检查依赖 ----
echo "📋 Step 1: 检查依赖..."

check_cmd() {
  if command -v "$1" &>/dev/null; then
    echo "  ✅ $1 $(command -v "$1")"
    return 0
  else
    echo "  ❌ $1 未找到"
    return 1
  fi
}

check_cmd claude || true
check_cmd python3 || true

# V9.1：bun 缺失则自动安装，不再询问
if ! command -v bun &>/dev/null; then
  echo ""
  echo "  🔧 未检测到 bun，自动安装中..."
  curl -fsSL https://bun.sh/install | bash >/dev/null 2>&1 || true
  export BUN_INSTALL="$HOME/.bun"
  export PATH="$BUN_INSTALL/bin:$PATH"
  # 幂等写入 ~/.zshrc
  if [ -f "$HOME/.zshrc" ] && ! grep -q 'BUN_INSTALL' "$HOME/.zshrc"; then
    printf '\n# bun (V9.1 auto-install)\nexport BUN_INSTALL="$HOME/.bun"\nexport PATH="$BUN_INSTALL/bin:$PATH"\n' >> "$HOME/.zshrc"
  fi
  if command -v bun &>/dev/null; then
    echo "  ✅ bun 自动安装完成：$(bun --version)"
  else
    echo "  ❌ bun 自动安装失败，请手动执行：curl -fsSL https://bun.sh/install | bash"
  fi
else
  echo "  ✅ bun $(command -v bun)"
fi

# V9.1：lark CLI 缺失则自动安装（飞书推送依赖）
if ! command -v lark &>/dev/null; then
  echo ""
  echo "  🔧 未检测到 lark CLI，自动安装中..."
  if command -v bun &>/dev/null; then
    bun install -g @larksuiteoapi/lark-cli >/dev/null 2>&1 || \
      npm install -g @larksuiteoapi/lark-cli >/dev/null 2>&1 || true
  fi
  if command -v lark &>/dev/null; then
    echo "  ✅ lark CLI 自动安装完成"
  else
    echo "  ⚠️  lark CLI 自动安装失败，飞书推送将退化为纯 HTTP 模式（仍可用）"
  fi
else
  echo "  ✅ lark $(command -v lark)"
fi

# 检查 Python 包
echo ""
echo "  检查 Python 包..."
python3 -c "import markdown" 2>/dev/null && echo "  ✅ markdown" || echo "  ❌ markdown (pip3 install markdown)"
python3 -c "import requests" 2>/dev/null && echo "  ✅ requests" || echo "  ❌ requests (pip3 install requests)"

# ---- Step 2: 创建配置文件 ----
echo ""
echo "📋 Step 2: 创建配置文件..."

# .env
ENV_FILE="$SCRIPT_DIR/server/.env"
ENV_EXAMPLE="$SCRIPT_DIR/server/.env.example"
if [ -f "$ENV_FILE" ]; then
  echo "  ⏭️  $ENV_FILE 已存在，跳过"
else
  if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    # 自动填入 SKILL_PATH
    sed -i.bak "s|SKILL_PATH=.*|SKILL_PATH=$SKILL_DIR|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    echo "  ✅ 已创建 $ENV_FILE（从 .env.example 复制）"
    echo "  ⚠️  请编辑此文件，填入你的飞书和微信凭据："
    echo "     $ENV_FILE"
  else
    echo "  ❌ $ENV_EXAMPLE 不存在"
  fi
fi

# config.json (根目录)
CONFIG_FILE="$SKILL_DIR/config.json"
CONFIG_EXAMPLE="$SKILL_DIR/config.json.example"
if [ -f "$CONFIG_FILE" ]; then
  echo "  ⏭️  $CONFIG_FILE 已存在，跳过"
else
  if [ -f "$CONFIG_EXAMPLE" ]; then
    cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
    echo "  ✅ 已创建 $CONFIG_FILE（从 config.json.example 复制）"
    echo "  ⚠️  请编辑此文件，填入你的微信公众号凭据"
  fi
fi

# ---- Step 3: 安装 Node 依赖 ----
echo ""
echo "📋 Step 3: 安装服务端依赖..."

if command -v bun &>/dev/null; then
  cd "$SCRIPT_DIR/server"
  bun install 2>/dev/null && echo "  ✅ bun install 完成" || echo "  ❌ bun install 失败"
  cd "$SKILL_DIR"
else
  echo "  ⏭️  bun 未安装，跳过"
fi

# ---- Step 3.6: 自动配置飞书 CLI（V9.1 新增） ----
echo ""
echo "📋 Step 3.6: 飞书 CLI 自动授权..."

if command -v lark &>/dev/null; then
  if [ -f "$ENV_FILE" ]; then
    # 从 .env 提取 APP_ID / APP_SECRET（忽略 quote）
    FEISHU_APP_ID=$(grep -E '^FEISHU_APP_ID=' "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
    FEISHU_APP_SECRET=$(grep -E '^FEISHU_APP_SECRET=' "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
    if [ -n "$FEISHU_APP_ID" ] && [ -n "$FEISHU_APP_SECRET" ] && [ "$FEISHU_APP_ID" != "your_app_id_here" ]; then
      # lark CLI 配置（容错多种子命令名）
      lark config set app_id "$FEISHU_APP_ID" 2>/dev/null || \
        lark login --app-id "$FEISHU_APP_ID" --app-secret "$FEISHU_APP_SECRET" 2>/dev/null || \
        true
      lark config set app_secret "$FEISHU_APP_SECRET" 2>/dev/null || true
      echo "  ✅ 飞书 CLI 已用 .env 凭据自动授权"
    else
      echo "  ⏭️  .env 尚未填写 FEISHU_APP_ID / FEISHU_APP_SECRET，跳过（可手动运行 lark login）"
    fi
  fi
else
  echo "  ⏭️  lark CLI 未安装，跳过（飞书推送将走纯 HTTP 模式）"
fi

# ---- Step 3.5: 自动注册定时任务（V9.0 新增，不询问用户） ----
echo ""
echo "📋 Step 3.5: 自动注册每日 10:00 定时任务..."

OS_NAME="$(uname -s)"
if [ "$OS_NAME" = "Darwin" ]; then
  # macOS · launchd
  PLIST_SRC="$SCRIPT_DIR/com.nsksd.daily-topics.plist"
  PLIST_DST="$HOME/Library/LaunchAgents/com.nsksd.daily-topics.plist"
  if [ -f "$PLIST_SRC" ]; then
    # 把模板里的 /tmp/nsksd-content-skill 替换成实际 Skill 路径
    sed "s|/tmp/nsksd-content-skill|$SKILL_DIR|g; s|/Users/suze|$HOME|g" "$PLIST_SRC" > "$PLIST_DST"
    mkdir -p "$SKILL_DIR/logs"
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load "$PLIST_DST" && echo "  ✅ launchd 定时任务已注册（每日 10:00）" || echo "  ❌ launchctl load 失败"
  else
    echo "  ❌ plist 模板不存在：$PLIST_SRC"
  fi
elif [[ "$OS_NAME" == MINGW* || "$OS_NAME" == CYGWIN* ]]; then
  echo "  ⚠️  检测到 Windows 环境，请改用 PowerShell 运行 scripts/setup.ps1"
else
  echo "  ⚠️  未知 OS：$OS_NAME，请手动配置 cron 每日 10:00 运行 scripts/run_nsksd_daily.sh"
fi

# ---- Step 4: 验证 ----
echo ""
echo "📋 Step 4: 快速验证..."

# 检查关键文件
for f in SKILL.md scripts/server/index.ts scripts/format/format.py scripts/format/publish.py scripts/run_nsksd_daily.sh; do
  if [ -f "$SKILL_DIR/$f" ]; then
    echo "  ✅ $f"
  else
    echo "  ❌ $f 缺失"
  fi
done

# 检查主题文件
theme_count=$(ls "$SKILL_DIR/themes/"*.json 2>/dev/null | wc -l | tr -d ' ')
echo "  ✅ 排版主题: ${theme_count} 个"

echo ""
echo "============================================"
echo "  ✅ 基础配置完成！"
echo ""
echo "  下一步："
echo "  1. 编辑 scripts/server/.env 填入凭据"
echo "  2. 编辑 config.json 填入微信公众号信息"
echo "  3. 启动服务测试："
echo "     cd scripts/server && source .env && bun run index.ts"
echo "  4. 设置定时任务（见 docs/scheduling.md）"
echo "============================================"
