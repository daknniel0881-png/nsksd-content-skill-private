#!/usr/bin/env bash
# ============================================================
# 日生研NSKSD · 凭据自动配置脚本
#
# 用法：bash scripts/setup-credentials.sh
#
# 自动获取：飞书 App ID / App Secret / Open ID
# 需要输入：微信 App ID / App Secret / 作者名
# ============================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$SKILL_DIR/scripts/server/.env"
CONFIG_FILE="$SKILL_DIR/config.json"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  日生研NSKSD · 凭据自动配置                       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 检查依赖 ──────────────────────────────────────────────

check_dep() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ 未找到 $1，请先安装："
    echo "   $2"
    return 1
  fi
}

check_dep "lark-cli" "npm install -g @nicepkg/lark-cli" || exit 1
check_dep "bun" "curl -fsSL https://bun.sh/install | bash" || exit 1
check_dep "python3" "请安装 Python 3.8+" || exit 1

# ── 第一步：飞书凭据（自动获取） ───────────────────────────

echo "━━━ 第一步：飞书凭据 ━━━"

LARK_CONFIG_OUTPUT=$(lark-cli config show 2>&1)
LARK_APP_ID=$(echo "$LARK_CONFIG_OUTPUT" | grep -o '"appId": *"[^"]*"' | head -1 | sed 's/.*: *"\(.*\)"/\1/')

if [ -z "$LARK_APP_ID" ]; then
  echo "⚠️  lark-cli 尚未配置飞书应用。"
  echo ""
  echo "请输入飞书应用凭据（从 https://open.feishu.cn/app 获取）："
  read -rp "  飞书 App ID: " LARK_APP_ID
  read -rsp "  飞书 App Secret: " LARK_APP_SECRET
  echo ""

  echo "$LARK_APP_SECRET" | lark-cli config init --app-id "$LARK_APP_ID" --app-secret-stdin --brand feishu
  echo "✅ lark-cli 配置完成"

  # 重新读取
  LARK_CONFIG_OUTPUT=$(lark-cli config show 2>&1)
else
  echo "✅ 检测到飞书应用: $LARK_APP_ID"
fi

# 获取 App Secret（从配置文件读取明文）
LARK_CONFIG_PATH=$(echo "$LARK_CONFIG_OUTPUT" | grep "Config file path:" | sed 's/Config file path: //')
if [ -n "$LARK_CONFIG_PATH" ] && [ -f "$LARK_CONFIG_PATH" ]; then
  LARK_APP_SECRET=$(python3 -c "import json; print(json.load(open('$LARK_CONFIG_PATH'))['appSecret'])" 2>/dev/null || echo "")
fi

if [ -z "${LARK_APP_SECRET:-}" ]; then
  echo "⚠️  无法从配置文件读取 App Secret"
  read -rsp "  请手动输入飞书 App Secret: " LARK_APP_SECRET
  echo ""
fi

# 获取 Open ID
TARGET_OPEN_ID=$(echo "$LARK_CONFIG_OUTPUT" | grep -oE 'ou_[a-f0-9]+' | head -1)
if [ -z "$TARGET_OPEN_ID" ]; then
  echo "⚠️  未找到关联用户的 Open ID"
  echo "   请先在飞书中给机器人发一条消息，然后重新运行此脚本。"
  echo "   或者手动输入："
  read -rp "  飞书 Open ID (ou_xxx): " TARGET_OPEN_ID
fi

echo "✅ 飞书 Open ID: $TARGET_OPEN_ID"
echo ""

# ── 第二步：微信凭据（需要输入） ───────────────────────────

echo "━━━ 第二步：微信公众号凭据 ━━━"

# 检查是否已有微信凭据
EXISTING_WX_ID=""
if [ -f "$CONFIG_FILE" ]; then
  EXISTING_WX_ID=$(python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
v = c.get('wechat',{}).get('app_id','')
print(v if v and 'YOUR_' not in v else '')
" 2>/dev/null || echo "")
fi

if [ -n "$EXISTING_WX_ID" ]; then
  echo "✅ 检测到已有微信凭据: $EXISTING_WX_ID"
  read -rp "  是否重新配置？(y/N) " RECONFIG_WX
  if [ "${RECONFIG_WX,,}" != "y" ]; then
    WECHAT_APP_ID="$EXISTING_WX_ID"
    WECHAT_APP_SECRET=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('wechat',{}).get('app_secret',''))" 2>/dev/null)
    WECHAT_AUTHOR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('wechat',{}).get('author',''))" 2>/dev/null)
  fi
fi

if [ -z "${WECHAT_APP_ID:-}" ]; then
  echo ""
  echo "请输入微信公众号凭据（从 https://mp.weixin.qq.com → 基本配置 获取）："
  read -rp "  微信 AppID: " WECHAT_APP_ID
  read -rsp "  微信 AppSecret: " WECHAT_APP_SECRET
  echo ""
  read -rp "  公众号作者名（显示在文章底部）: " WECHAT_AUTHOR
fi

echo ""

# ── 第三步：IP 白名单提醒 ──────────────────────────────────

echo "━━━ 第三步：IP 白名单 ━━━"
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || echo "无法获取")
echo "  当前出口 IP: $CURRENT_IP"
echo "  ⚠️  请确保此 IP 已添加到公众号的 IP 白名单中"
echo "  （公众号后台 → 设置与开发 → 基本配置 → IP白名单）"
echo ""

# ── 第四步：写入配置文件 ───────────────────────────────────

echo "━━━ 第四步：写入配置 ━━━"

# 写入 .env
cat > "$ENV_FILE" << ENVEOF
# 飞书应用凭据（自动配置于 $(date '+%Y-%m-%d %H:%M')）
LARK_APP_ID=${LARK_APP_ID}
LARK_APP_SECRET=${LARK_APP_SECRET}
TARGET_OPEN_ID=${TARGET_OPEN_ID}

SKILL_PATH=${SKILL_DIR}
PORT=9800

# 微信公众号凭据
WECHAT_APP_ID=${WECHAT_APP_ID}
WECHAT_APP_SECRET=${WECHAT_APP_SECRET}
ENVEOF

echo "✅ .env 已写入"

# 写入 config.json
python3 -c "
import json
config = {
    'output_dir': '/tmp/wechat-format',
    'vault_root': '/path/to/obsidian/vault',
    'settings': {
        'default_theme': 'mint-fresh',
        'auto_open_browser': False
    },
    'wechat': {
        'app_id': '${WECHAT_APP_ID}',
        'app_secret': '${WECHAT_APP_SECRET}',
        'author': '${WECHAT_AUTHOR:-}'
    }
}
with open('$CONFIG_FILE', 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
"

echo "✅ config.json 已写入"

# ── 第五步：安装依赖 ───────────────────────────────────────

echo ""
echo "━━━ 第五步：安装依赖 ━━━"
cd "$SKILL_DIR/scripts/server" && bun install --silent 2>/dev/null && echo "✅ Node 依赖已安装" || echo "⚠️  Node 依赖安装失败，请手动 cd scripts/server && bun install"
pip3 install -q markdown requests python-dotenv 2>/dev/null && echo "✅ Python 依赖已安装" || echo "⚠️  Python 依赖安装失败，请手动 pip3 install markdown requests python-dotenv"

# ── 第六步：验证 ───────────────────────────────────────────

echo ""
echo "━━━ 第六步：验证配置 ━━━"

# 验证飞书
echo -n "  飞书: "
LARK_TEST=$(lark-cli im +messages-send --user-id "$TARGET_OPEN_ID" --text "🔧 日生研内容创作 Skill 配置成功！" --as bot 2>&1)
if echo "$LARK_TEST" | grep -q '"ok": true'; then
  echo "✅ 发送测试消息成功"
else
  echo "❌ 发送失败，请检查应用权限和发布状态"
fi

# 验证微信
echo -n "  微信: "
WX_TEST=$(curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${WECHAT_APP_ID}&secret=${WECHAT_APP_SECRET}")
if echo "$WX_TEST" | grep -q "access_token"; then
  echo "✅ access_token 获取成功"
else
  ERRCODE=$(echo "$WX_TEST" | python3 -c "import sys,json; print(json.load(sys.stdin).get('errcode','?'))" 2>/dev/null || echo "?")
  if [ "$ERRCODE" = "40164" ]; then
    echo "❌ IP 不在白名单，请添加: $CURRENT_IP"
  elif [ "$ERRCODE" = "40001" ] || [ "$ERRCODE" = "40125" ]; then
    echo "❌ AppSecret 错误，请检查"
  else
    echo "❌ 失败 (errcode=$ERRCODE)"
  fi
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  配置完成！输入 /nsksd 开始使用内容创作工作流"
echo "══════════════════════════════════════════════════"
echo ""
