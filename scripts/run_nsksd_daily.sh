#!/bin/bash
# ============================================================
# 日生研NSKSD · 每日选题定时推送（v4 精简版 · 2026-04-21 起生效）
#
# 工作流（每天 10:00 由 LaunchAgent 触发）:
#   Step 1: 调 claude -p 按 SKILL.md 生成 10 条选题
#   Step 2: 解析选题 → 构造 v4 多选卡（平铺 + 勾选 + 提交）
#   Step 3: 确保 listener 运行 → 推卡
#   Step 4: 确保 trigger-watcher 运行 → 等待用户勾选
#
# 相比 v8.3 的变化:
#   - 删除 bun server（整个 scripts/server/ 废弃）
#   - 删除 send-topic-card.ts / daily-topics.sh（V1 纯展示卡）
#   - 删除云文档 A 创建流程（直接靠多选卡交互）
#   - 删除清单卡（只保留多选卡一种形态）
#   - 新增 trigger-watcher 守护进程（轮询 triggers/ 调 claude -p 跑流水线）
#
# 手动运行:
#   ./run_nsksd_daily.sh             # 完整流程
#   ./run_nsksd_daily.sh --card-only # 跳过生成选题,用 /tmp 已有文件发卡
#   ./run_nsksd_daily.sh --start-daemons # 只启动 listener+watcher
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
INTERACTIVE_DIR="$SCRIPT_DIR/interactive"
LOG_DIR="$SKILL_DIR/logs"
TODAY=$(date +%Y-%m-%d)
SESSION_ID="daily-$TODAY"
LOG_FILE="$LOG_DIR/daily-$TODAY.log"

TOPICS_MD="/tmp/nsksd-topics-$TODAY.md"
TOPICS_JSON="/tmp/nsksd-topics-$TODAY.json"
CARD_JSON="/tmp/nsksd-card-$TODAY.json"

LISTENER_PID_FILE="/tmp/nsksd-listener.pid"
WATCHER_PID_FILE="/tmp/nsksd-watcher.pid"

mkdir -p "$LOG_DIR"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg" | tee -a "$LOG_FILE"
}

die() {
  log "FATAL: $1"
  exit 1
}

# ---- 环境变量 ----
# 凭证硬铁律：仅从环境变量或 ~/.nsksd-content/config.json 读，仓库内零硬编码
[ -n "${LARK_APP_ID:-}" ] || die "LARK_APP_ID 未设置（请在 ~/.nsksd-content/config.json 配置或 export）"
[ -n "${LARK_APP_SECRET:-}" ] || die "LARK_APP_SECRET 未设置"
[ -n "${TARGET_OPEN_ID:-}" ] || die "TARGET_OPEN_ID 未设置"
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.bun/bin:$HOME/.local/bin:$PATH"
export SKILL_PATH="$SKILL_DIR"
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"

# ============================================================
# Step 1: 生成 10 选题（claude -p）
# ============================================================
generate_topics() {
  log "Step 1: 调 claude -p 生成 10 选题..."
  [ -n "$CLAUDE_BIN" ] || die "claude CLI 未找到"

  local prompt
  prompt=$(cat <<EOF
请阅读 $SKILL_DIR/SKILL.md 了解 V9.7 工作流。
【必读三件套】
- $SKILL_DIR/references/topic-selection-rules.md（八维坐标系 + 三层去重 + 反面示例）
- $SKILL_DIR/references/title-playbook.md（45 标题公式 + 张力 6 维 + 三库禁用词 + 医广红线）
- $SKILL_DIR/references/topic-library/README.md（分块资讯池 + 8 招商角度硬约束）

执行【Step 1 · 选题生成】:
1. 读当日热点 $SKILL_DIR/references/topic-library/hotspots/$(date +%F).json（无则跳过）
2. 查 $SKILL_DIR/logs/topic-history.jsonl 做 30 天三维指纹去重（文件不存在就当空集合）
3. 生成 >= 10 个选题（S/A/B 分层），至少 3 个结合当日热点
4. 每个选题包含：标题/维度(M1-M8)/公式(F1-F45)/角度/数据点(含URL)/目标人群/内容线/合规分级/等级/评分/发布时机

【V9.7 硬约束 · 选题维度配比】
- 10 选题必须覆盖 ≥ 5 个不同维度（M1-M8）
- **M7 招商场景单日 ≤ 1 条**（硬线，违反就重生成）
- M6 产品科普单日 ≤ 1 条；M6 + M7 合计 ≤ 2 条
- C 端维度（M1 医学循证 + M3 节气养生 + M4 用户痛点 + M8 名人古法）占比 ≥ 60%（7/10 以上给 C 端）
- 禁止主人群（门店老板 / 美容院老板 / 养生馆老板 / 分销商）超过 1 条

【V9.7 反面示例 · 禁止生成类似变体】
❌ 美容院下一个利润增长点，不在脸上
❌ 养生馆老板：你还在靠手艺赚钱吗
❌ 社区门店如何靠一款产品锁定 500 个家庭
❌ 血管健康到底怎么管（无数字无人群）
❌ 根治血栓的方法（触医广红线）

【V9.7 标题必过 · 张力 6 维命中 ≥3 项】
[对比反差] [具体数字] [悬念好奇] [冲突争议] [时间承诺] [结果承诺]
每条标题至少命中 3 项。公众号标题 18-25 字，关键词前置到前 10 字。

【V9.7 标题禁用词 · 三库扫描】
- 医广红线：治疗/治愈/根治/当天见效/最好/最佳/第一/唯一/国家级
- 曲率风格禁用：赋能/链路/飞轮/颗粒度/抓手/闭环/破圈/放大招/炸裂/颠覆
- 禁用句式：「不是…而是…」「不是…是…」破折号 ——

严禁：捏造数据 / 捏造 URL / 捏造机构 / 日本表述（日本进口、日式工艺）。找不到就写"行业内流传"或删掉。

【输出格式严格要求】
文末用 \`\`\`json 代码块输出 JSON 数组,字段:
  - value: 选题编号(topic_1, topic_2, ... 按 1-10 原序)
  - text: 完整 Markdown 文本(例 "🏆 选题1 · 标题（M4/F21，90分）")
至少 10 个 options。
EOF
)

  "$CLAUDE_BIN" -p "$prompt" > "$TOPICS_MD" 2>>"$LOG_FILE"
  [ -s "$TOPICS_MD" ] || die "选题生成失败"

  # 提取 JSON
  python3 <<PYEOF
import re, json, sys
content = open("$TOPICS_MD").read()
m = re.search(r'\`\`\`json\s*\n(.*?)\n\`\`\`', content, re.DOTALL)
if not m:
    print("ERROR: 无法从选题文件提取 json 代码块", file=sys.stderr)
    sys.exit(1)
data = json.loads(m.group(1))
if len(data) < 10:
    print(f"ERROR: options 数量 {len(data)} < 10", file=sys.stderr)
    sys.exit(1)
json.dump(data, open("$TOPICS_JSON", "w"), ensure_ascii=False, indent=2)
print(f"✅ 已提取 {len(data)} 个选题")
PYEOF

  [ -s "$TOPICS_JSON" ] || die "选题 JSON 解析失败"
  log "  ✅ 选题文件: $TOPICS_JSON"
}

# ============================================================
# Step 2: 构造 v4 多选卡
# ============================================================
build_card() {
  log "Step 2: 构造 v4 多选卡..."

  python3 <<PYEOF
import json, sys
sys.path.insert(0, "$INTERACTIVE_DIR")
from card_builder import multi_choice_card

options = json.load(open("$TOPICS_JSON"))
card = multi_choice_card(
    session_id="$SESSION_ID",
    step="topic_select",
    title="日生研NSKSD · 每日选题多选 ($TODAY)",
    intro_md=f"💡 **今日 {len(options)} 条选题**\n\n按 V9.1 六维坐标系生成 · 勾选你想创作的,点底部按钮一次提交",
    options=options,
)
json.dump(card, open("$CARD_JSON", "w"), ensure_ascii=False, indent=2)
print(f"✅ 卡片构造完成: {len(options)} 选项")
PYEOF

  [ -s "$CARD_JSON" ] || die "卡片构造失败"
}

# ============================================================
# Step 3: 确保 listener 运行 + 推卡
# ============================================================
ensure_listener() {
  if [ -f "$LISTENER_PID_FILE" ] && kill -0 "$(cat "$LISTENER_PID_FILE")" 2>/dev/null; then
    log "  listener 已在运行 (PID: $(cat "$LISTENER_PID_FILE"))"
    return
  fi
  log "  启动 listener..."
  cd "$INTERACTIVE_DIR"
  nohup python3 lark_ws_listener.py > "$LOG_DIR/listener-$TODAY.log" 2>&1 &
  echo $! > "$LISTENER_PID_FILE"
  sleep 3
  log "  ✅ listener 已启动 (PID: $(cat "$LISTENER_PID_FILE"))"
}

send_card() {
  log "Step 3: 推送多选卡到飞书..."
  ensure_listener

  if ! command -v lark-cli >/dev/null 2>&1; then
    die "lark-cli 未安装"
  fi

  local resp
  resp=$(lark-cli im +messages-send --as bot --user-id "$TARGET_OPEN_ID" \
    --msg-type interactive --content "$(cat "$CARD_JSON")" 2>&1)
  local msg_id
  msg_id=$(echo "$resp" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['data']['message_id'])" 2>/dev/null || echo "")
  [ -n "$msg_id" ] || die "推卡失败: $resp"
  log "  ✅ 卡片已推送 (message_id: $msg_id)"
}

# ============================================================
# Step 4: 确保 trigger-watcher 运行
# ============================================================
ensure_watcher() {
  log "Step 4: 确保 trigger-watcher 运行..."
  if [ -f "$WATCHER_PID_FILE" ] && kill -0 "$(cat "$WATCHER_PID_FILE")" 2>/dev/null; then
    log "  watcher 已在运行 (PID: $(cat "$WATCHER_PID_FILE"))"
    return
  fi
  cd "$INTERACTIVE_DIR"
  nohup bash trigger_watcher.sh > "$LOG_DIR/watcher-$TODAY.log" 2>&1 &
  echo $! > "$WATCHER_PID_FILE"
  sleep 2
  log "  ✅ watcher 已启动 (PID: $(cat "$WATCHER_PID_FILE"))"
}

# ============================================================
# 主流程
# ============================================================
main() {
  log "============================================"
  log "日生研NSKSD · 每日选题推送 v4  · $TODAY"
  log "============================================"

  case "${1:-full}" in
    --card-only)
      build_card
      send_card
      ensure_watcher
      ;;
    --start-daemons)
      ensure_listener
      ensure_watcher
      log "✅ 守护进程已启动"
      ;;
    full|*)
      generate_topics
      build_card
      send_card
      ensure_watcher
      ;;
  esac

  log "============================================"
  log "✅ 完成 · 等待用户在飞书勾选选题"
  log "  listener log: $LOG_DIR/listener-$TODAY.log"
  log "  watcher log:  $LOG_DIR/watcher-$TODAY.log"
  log "  daily log:    $LOG_FILE"
  log "============================================"
}

main "$@"
