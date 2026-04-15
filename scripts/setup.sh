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

missing=0
check_cmd claude || missing=1
check_cmd bun || missing=1
check_cmd python3 || missing=1

if [ "$missing" = "1" ]; then
  echo ""
  echo "⚠️  缺少必要依赖，请先安装："
  echo "  - Claude Code: https://docs.anthropic.com/claude-code"
  echo "  - Bun: curl -fsSL https://bun.sh/install | bash"
  echo "  - Python 3: brew install python3 (Mac) 或 https://python.org (Windows)"
  echo ""
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
