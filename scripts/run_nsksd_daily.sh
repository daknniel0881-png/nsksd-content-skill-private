#!/bin/bash
# ============================================================
# 日生研NSKSD · 每日选题定时推送脚本（v8.3）
#
# 触发时间：每天早上 10:00（北京时间）
#
# v8.3 行为变更：
#   本脚本只负责 Step 1（不再一口气跑到草稿箱）
#   Step 1 = 生成 10 选题 + 创建飞书云文档 A + 启动监听 + 推多选卡
#   用户在飞书勾选后，后续流程由 master-orchestrator 按 config.json
#   的 default_mode（auto/guided）接管继续跑。
#
# 设计考量：
#   10 点时用户大概率不在电脑前，封面/主题/合规都需要人眼确认，
#   跑到草稿箱风险大。改为"备好选题等勾选"更可控。
#
# 由 LaunchAgent (Mac) 定时触发，也可手动运行：./run_nsksd_daily.sh
# ============================================================

set -euo pipefail

# ---- 路径配置 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SERVER_DIR="$SCRIPT_DIR/server"
LOG_DIR="$SKILL_DIR/logs"
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/daily-$TODAY.log"

mkdir -p "$LOG_DIR"

# ---- 工具函数 ----
log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

die() {
  log "FATAL: $1"
  notify_error "$1" || true
  exit 1
}

# ---- 环境变量 ----
if [ -f "$SERVER_DIR/.env" ]; then
  set -a
  source "$SERVER_DIR/.env"
  set +a
fi

export LARK_APP_ID="${LARK_APP_ID:-}"
export LARK_APP_SECRET="${LARK_APP_SECRET:-}"
export TARGET_OPEN_ID="${TARGET_OPEN_ID:-}"

if [ -z "$LARK_APP_ID" ] || [ -z "$LARK_APP_SECRET" ] || [ -z "$TARGET_OPEN_ID" ]; then
  die "缺少飞书凭据。请先配置 scripts/server/.env（参考 .env.example）"
fi
export SKILL_PATH="$SKILL_DIR"

# ---- 输出文件 ----
TOPICS_MD="/tmp/nsksd-topics-$TODAY.md"
TOPICS_JSON="/tmp/nsksd-topics-$TODAY.json"
DOC_URL_FILE="/tmp/nsksd-doc-url-$TODAY.txt"
SERVER_PID_FILE="/tmp/nsksd-ws-listener.pid"

# ---- 依赖检查 ----
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.bun/bin:$HOME/.local/bin:$PATH"
CLAUDE_BIN="${CLAUDE_BIN:-$(which claude 2>/dev/null || echo "")}"
BUN_BIN="${BUN_BIN:-$(which bun 2>/dev/null || echo "")}"

get_tenant_token() {
  local resp
  resp=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
    -H "Content-Type: application/json" \
    -d "{\"app_id\": \"$LARK_APP_ID\", \"app_secret\": \"$LARK_APP_SECRET\"}")
  echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])" 2>/dev/null
}

notify_error() {
  local msg="$1"
  local token
  token=$(get_tenant_token) || return 1
  curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "{
      \"receive_id\": \"$TARGET_OPEN_ID\",
      \"msg_type\": \"text\",
      \"content\": \"{\\\"text\\\":\\\"[NSKSD日报 v8.3] Step 1 推送失败: $msg\\\"}\"
    }" > /dev/null 2>&1
}

# ============================================================
# STEP 1a: 生成 10 选题（调用 topic-scout Agent）
# ============================================================
generate_topics() {
  log "STEP 1a: 调用 topic-scout 生成 10 个选题..."

  [ -n "$CLAUDE_BIN" ] || die "claude CLI 未找到，请先安装"

  # 读当前模式供下游 master-orchestrator 接管时使用
  local current_mode
  current_mode=$(python3 "$SKILL_DIR/scripts/mode_manager.py" get 2>/dev/null || echo "auto")
  log "当前保存模式: $current_mode（勾选后按此模式继续）"

  local prompt
  prompt=$(cat <<EOF
请阅读 $SKILL_DIR/SKILL.md 了解 v8.3 工作流。
然后参考 $SKILL_DIR/agents/topic-scout.md 执行【选题侦察】任务。

要求：
1. 读 references/knowledge-base.md / topic-library.md / compliance.md
2. 查 logs/topic-history.jsonl 做 30 天三维指纹去重
3. 生成 20 候选 → 输出 10 个 S/A/B 级选题
4. 每个选题包含：标题、内容线、核心角度、目标人群、合规分级、五维评分、3 个备选标题、大纲摘要
5. 文末用 \`\`\`json 代码块输出 JSON 数组，字段：index/title/grade/line/score/compliance/angle/audience/outline/alt_titles
EOF
)

  "$CLAUDE_BIN" -p "$prompt" > "$TOPICS_MD" 2>>"$LOG_FILE"
  [ $? -eq 0 ] && [ -s "$TOPICS_MD" ] || die "topic-scout 选题生成失败"

  # 提取 JSON
  python3 -c "
import re, sys
content = open('$TOPICS_MD').read()
m = re.search(r'\`\`\`json\s*\n(.*?)\n\`\`\`', content, re.DOTALL)
if m:
    print(m.group(1))
else:
    m = re.search(r'(\[[\s\S]*\])\s*\$', content)
    sys.exit(0 if m and sys.stdout.write(m.group(1)) else 1)
" > "$TOPICS_JSON" 2>/dev/null

  [ -s "$TOPICS_JSON" ] || die "无法从 topic-scout 输出提取 JSON"

  local count
  count=$(python3 -c "import json; print(len(json.load(open('$TOPICS_JSON'))))" 2>/dev/null || echo "0")
  log "STEP 1a 完成：生成 $count 个选题 → $TOPICS_JSON"
}

# ============================================================
# STEP 1b: 创建飞书云文档 A（选题预审）
# ============================================================
create_feishu_doc() {
  log "STEP 1b: 创建飞书云文档 A（选题预审）..."

  local token
  token=$(get_tenant_token) || die "获取飞书 token 失败"

  local doc_title="日生研NSKSD · ${TODAY} 选题预审（云文档 A）"
  local create_resp
  create_resp=$(curl -s -X POST "https://open.feishu.cn/open-apis/docx/v1/documents" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "{\"title\": \"$doc_title\"}")

  local doc_id
  doc_id=$(echo "$create_resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['document']['document_id'])" 2>/dev/null)

  if [ -z "$doc_id" ]; then
    log "WARNING: 创建云文档失败，跳过：$create_resp"
    echo "" > "$DOC_URL_FILE"
    return
  fi

  log "云文档 A 已创建: $doc_id"

  # 批量写入 blocks
  TOPICS_JSON_PATH="$TOPICS_JSON" TOKEN="$token" DOC_ID="$doc_id" python3 << 'PYEOF'
import json, os, sys, urllib.request

token = os.environ["TOKEN"]
doc_id = os.environ["DOC_ID"]
try:
    topics = json.load(open(os.environ["TOPICS_JSON_PATH"]))
except Exception:
    topics = []

blocks = []
grade_info = {"S": "S级 (立即可写)", "A": "A级 (值得写)", "B": "B级 (备选)"}

for grade in ["S", "A", "B"]:
    group = [t for t in topics if t.get("grade") == grade]
    if not group:
        continue
    blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": grade_info[grade]}}]}})
    for t in group:
        blocks.append({"block_type": 5, "heading3": {"elements": [
            {"text_run": {"content": f"{t.get('index','?')}. {t.get('title','')}"}}]}})
        for line in [
            f"内容线: {t.get('line','')} | 合规: {t.get('compliance','🟢')} | 评分: {t.get('score','')}分",
            f"核心角度: {t.get('angle','')}",
            f"目标人群: {t.get('audience','')}",
            f"大纲: {t.get('outline','')}" if t.get("outline") else "",
        ]:
            if line:
                blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line}}]}})
        if t.get("alt_titles"):
            blocks.append({"block_type": 2, "text": {"elements": [
                {"text_run": {"content": "备选标题:", "text_element_style": {"bold": True}}}]}})
            for alt in t["alt_titles"]:
                blocks.append({"block_type": 16, "bullet": {"elements": [{"text_run": {"content": alt}}]}})
        blocks.append({"block_type": 22})

for i in range(0, len(blocks), 50):
    batch = blocks[i:i+50]
    data = json.dumps({"children": batch, "index": -1}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST")
    try:
        urllib.request.urlopen(req).read()
    except Exception as e:
        print(f"WARN: 写 block 失败: {e}", file=sys.stderr)

print(f"云文档 A 内容写入完成，共 {len(blocks)} blocks")
PYEOF

  # 授权用户访问
  curl -s -X POST "https://open.feishu.cn/open-apis/drive/v1/permissions/${doc_id}/members?type=docx" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "{\"member_type\":\"openid\",\"member_id\":\"$TARGET_OPEN_ID\",\"perm\":\"full_access\"}" > /dev/null 2>&1

  local doc_url="https://bytedance.feishu.cn/docx/$doc_id"
  echo "$doc_url" > "$DOC_URL_FILE"
  log "STEP 1b 完成: $doc_url"
}

# ============================================================
# STEP 1c: 启动 WSClient 监听服务
# ============================================================
start_listener() {
  log "STEP 1c: 启动 WSClient 监听服务..."

  if [ -z "$BUN_BIN" ]; then
    log "WARNING: bun 未找到，跳过监听。手动启动：cd $SERVER_DIR && bun run index.ts"
    return
  fi

  if [ -f "$SERVER_PID_FILE" ] && kill -0 "$(cat "$SERVER_PID_FILE")" 2>/dev/null; then
    log "监听服务已在运行 (PID: $(cat "$SERVER_PID_FILE"))"
  else
    cd "$SERVER_DIR"
    nohup "$BUN_BIN" run index.ts >> "$LOG_DIR/server.log" 2>&1 &
    echo $! > "$SERVER_PID_FILE"
    log "监听服务已启动 (PID: $!)"
  fi

  # 注册今日选题到监听服务
  sleep 3
  if [ -s "$TOPICS_JSON" ]; then
    curl -s -X POST "http://localhost:9800/register-topics" \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "import json; print(json.dumps({'topics': json.load(open('$TOPICS_JSON'))}, ensure_ascii=False))")" \
      > /dev/null 2>&1 && log "选题已注册到监听服务" || log "WARN: 注册选题失败"
  fi
}

# ============================================================
# STEP 1d: 推送飞书多选卡
# ============================================================
send_topic_cards() {
  log "STEP 1d: 推送飞书多选卡..."

  # 等监听就绪
  local retries=0
  while [ $retries -lt 10 ]; do
    curl -s http://localhost:9800/health > /dev/null 2>&1 && break
    retries=$((retries + 1))
    sleep 2
  done
  [ $retries -lt 10 ] || die "监听服务未就绪，无法发卡片"

  local doc_url=""
  [ -s "$DOC_URL_FILE" ] && doc_url=$(cat "$DOC_URL_FILE")

  # 清单卡（选题概览 + 云文档链接）
  curl -s -X POST http://localhost:9800/send-summary-card \
    -H 'Content-Type: application/json' \
    -d "{\"doc_url\": \"$doc_url\"}" > /dev/null 2>&1 && log "清单卡已推送"

  sleep 1

  # 多选卡（勾选触发后续流程）
  local resp
  resp=$(curl -s -X POST http://localhost:9800/send-card -H 'Content-Type: application/json' -d '{}')
  local code
  code=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',-1))" 2>/dev/null || echo "-1")
  [ "$code" = "0" ] && log "多选卡已推送" || die "多选卡推送失败: $resp"
}

# ============================================================
# 主流程（v8.3：只跑 Step 1）
# ============================================================
main() {
  log "============================================"
  log "日生研NSKSD · 每日 Step 1 定时推送 (v8.3)"
  log "日期: $TODAY"
  log "行为: 只生成选题 + 云文档 A + 推多选卡"
  log "     用户勾选后由 master-orchestrator 按保存模式接管"
  log "============================================"

  generate_topics      # 1a: 选题
  create_feishu_doc    # 1b: 云文档 A
  start_listener       # 1c: 启动监听
  send_topic_cards     # 1d: 推多选卡

  log "============================================"
  log "✅ Step 1 完成！等用户在飞书勾选选题"
  log "  选题 MD : $TOPICS_MD"
  log "  选题 JSON: $TOPICS_JSON"
  log "  云文档 A: $(cat "$DOC_URL_FILE" 2>/dev/null || echo '(未生成)')"
  log "  日志    : $LOG_FILE"
  log "  后续    : 用户勾选后，master-orchestrator 按 mode_manager 保存的模式接管"
  log "============================================"
}

main "$@"
