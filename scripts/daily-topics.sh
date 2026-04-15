#!/bin/bash
# ============================================================
# 日生研NSKSD · 每日选题自动化脚本（Mac/Linux）
#
# 功能：
# 1. 调用Claude CLI生成选题
# 2. 发送V2多选卡片到飞书
# 3. 启动WSClient长连接监听服务
#
# 用法：
#   ./daily-topics.sh              # 完整流程
#   ./daily-topics.sh --server     # 只启动回调服务器
#   ./daily-topics.sh --card       # 只发送卡片（使用已有选题）
# ============================================================

set -euo pipefail

# ---- 配置 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
TOPICS_OUTPUT="/tmp/nsksd-topics-result.md"
SERVER_PID_FILE="/tmp/nsksd-ws-listener.pid"
LOG_DIR="$SKILL_DIR/logs"
TODAY=$(date +%Y-%m-%d)

# 飞书配置（请修改为实际值）
export LARK_APP_ID="${LARK_APP_ID:-}"
export LARK_APP_SECRET="${LARK_APP_SECRET:-}"
export TARGET_OPEN_ID="${TARGET_OPEN_ID:-}"
export CALLBACK_SERVER="${CALLBACK_SERVER:-http://localhost:9800}"
export SKILL_PATH="$SKILL_DIR"

mkdir -p "$LOG_DIR"

# ---- 函数 ----

log() {
  echo "[$(date '+%H:%M:%S')] $1"
}

# 启动WSClient长连接监听服务
start_server() {
  # 加载.env
  if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
  fi

  # 检查是否已在运行
  if [ -f "$SERVER_PID_FILE" ] && kill -0 "$(cat "$SERVER_PID_FILE")" 2>/dev/null; then
    log "✅ 监听服务已在运行 (PID: $(cat "$SERVER_PID_FILE"))"
    return
  fi

  log "🚀 启动WSClient长连接监听服务..."
  cd "$SCRIPT_DIR/server"
  nohup bun run index.ts > "$LOG_DIR/server-$TODAY.log" 2>&1 &
  echo $! > "$SERVER_PID_FILE"
  log "✅ 监听服务已启动 (PID: $!)"
  sleep 3

  # 健康检查
  if curl -sf "http://localhost:9800/health" > /dev/null 2>&1; then
    log "✅ 健康检查通过（WSClient长连接模式）"
  else
    log "⚠️ 服务可能还在启动中，请查看日志: $LOG_DIR/server-$TODAY.log"
  fi
}

# 停止监听服务
stop_server() {
  if [ -f "$SERVER_PID_FILE" ]; then
    local pid=$(cat "$SERVER_PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      log "✅ 监听服务已停止 (PID: $pid)"
    fi
    rm -f "$SERVER_PID_FILE"
  fi
}

# 生成选题
generate_topics() {
  log "📝 正在生成选题..."

  local prompt="请阅读 $SKILL_DIR/SKILL.md 了解工作流。
然后阅读以下参考文件：
- $SKILL_DIR/references/knowledge-base.md
- $SKILL_DIR/references/topic-library.md
- $SKILL_DIR/references/compliance.md

现在执行"阶段一：情报收集+选题生成"，生成10个选题。
按S/A/B分级，每个选题包含：标题、内容线、目标人群、合规分级、五维评分、3个标题选项、写作大纲。
严格遵循SKILL.md中的选题生成规范。"

  claude -p "$prompt" > "$TOPICS_OUTPUT" 2>"$LOG_DIR/claude-topics-$TODAY.log"

  if [ $? -eq 0 ] && [ -s "$TOPICS_OUTPUT" ]; then
    log "✅ 选题生成完成: $TOPICS_OUTPUT"
  else
    log "❌ 选题生成失败，请查看日志: $LOG_DIR/claude-topics-$TODAY.log"
    exit 1
  fi
}

# 发送卡片
send_card() {
  log "📤 发送选题卡片到飞书..."
  cd "$SCRIPT_DIR"
  bun run send-topic-card.ts "$TOPICS_OUTPUT" 2>&1 | tee "$LOG_DIR/card-$TODAY.log"
}

# ---- 主流程 ----

case "${1:-full}" in
  --server)
    start_server
    log "服务器运行中，按 Ctrl+C 停止"
    tail -f "$LOG_DIR/server-$TODAY.log"
    ;;
  --stop)
    stop_server
    ;;
  --card)
    start_server
    send_card
    ;;
  --generate)
    generate_topics
    ;;
  full|*)
    log "🏭 日生研NSKSD · 每日选题自动化"
    log "================================"
    start_server
    generate_topics
    send_card
    log "================================"
    log "✅ 全部完成！在飞书回复选题编号即可触发写稿"
    log "   监听服务日志: $LOG_DIR/server-$TODAY.log"
    log "   回复格式：1 3 5（空格/逗号/顿号分隔均可）"
    ;;
esac
