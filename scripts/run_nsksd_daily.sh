#!/bin/bash
# ============================================================
# 日生研NSKSD · 每日选题定时推送脚本
#
# 触发时间：每天早上10:00（北京时间）
# 流程：生成选题 → 创建飞书云文档 → 推送选题卡片 → 启动监听服务
#
# 由 LaunchAgent (Mac) 或 Task Scheduler (Windows) 定时触发
# 也可以手动运行：./run_nsksd_daily.sh
# ============================================================

set -euo pipefail

# ---- 路径配置 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SERVER_DIR="$SCRIPT_DIR/server"
LOG_DIR="$SKILL_DIR/logs"
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/daily-$TODAY.log"

# ---- 环境变量 ----
# 优先从 server/.env 加载
if [ -f "$SERVER_DIR/.env" ]; then
  set -a
  source "$SERVER_DIR/.env"
  set +a
fi

export LARK_APP_ID="${LARK_APP_ID:-}"
export LARK_APP_SECRET="${LARK_APP_SECRET:-}"
export TARGET_OPEN_ID="${TARGET_OPEN_ID:-}"

# 凭据检查
if [ -z "$LARK_APP_ID" ] || [ -z "$LARK_APP_SECRET" ] || [ -z "$TARGET_OPEN_ID" ]; then
  die "缺少必要的环境变量。请先配置 scripts/server/.env（参考 scripts/server/.env.example）"
fi
export SKILL_PATH="$SKILL_DIR"

# ---- 输出文件 ----
TOPICS_MD="/tmp/nsksd-topics-$TODAY.md"
TOPICS_JSON="/tmp/nsksd-topics-$TODAY.json"
DOC_URL_FILE="/tmp/nsksd-doc-url-$TODAY.txt"
SERVER_PID_FILE="/tmp/nsksd-ws-listener.pid"

# ---- 依赖检查 ----
CLAUDE_BIN="${CLAUDE_BIN:-$(which claude 2>/dev/null || echo "")}"
BUN_BIN="${BUN_BIN:-$(which bun 2>/dev/null || echo "")}"

# macOS launchd 环境下 PATH 可能不全，补一下常见路径
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.bun/bin:$HOME/.local/bin:$PATH"

if [ -z "$CLAUDE_BIN" ]; then
  CLAUDE_BIN=$(which claude 2>/dev/null || echo "")
fi
if [ -z "$BUN_BIN" ]; then
  BUN_BIN=$(which bun 2>/dev/null || echo "")
fi

mkdir -p "$LOG_DIR"

# ---- 工具函数 ----

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

die() {
  log "FATAL: $1"
  # 推送失败通知到飞书
  notify_error "$1" || true
  exit 1
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
      \"content\": \"{\\\"text\\\":\\\"[NSKSD日报] 今日选题推送失败: $msg\\\"}\"
    }" > /dev/null 2>&1
}

get_tenant_token() {
  local resp
  resp=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
    -H "Content-Type: application/json" \
    -d "{\"app_id\": \"$LARK_APP_ID\", \"app_secret\": \"$LARK_APP_SECRET\"}")

  echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])" 2>/dev/null
}

# ============================================================
# STEP 1: 生成选题
# ============================================================

generate_topics() {
  log "STEP 1: 生成选题..."

  if [ -z "$CLAUDE_BIN" ]; then
    die "claude CLI 未找到，请确认已安装"
  fi

  local prompt="请阅读 $SKILL_DIR/SKILL.md 了解工作流。
然后阅读以下参考文件：
- $SKILL_DIR/references/knowledge-base.md
- $SKILL_DIR/references/topic-library.md
- $SKILL_DIR/references/compliance.md

现在执行"阶段一：情报收集+选题生成"，生成10个选题。

要求：
1. 按S/A/B分级，每个选题包含：标题、内容线、核心角度、目标人群、合规分级、五维评分
2. 每个选题附3个标题备选和简要大纲框架
3. 严格遵循SKILL.md中的选题生成规范
4. 输出格式严格按照SKILL.md阶段一的输出格式

同时，请将选题以JSON格式额外输出一份，放在文末的 \`\`\`json 代码块中，格式如下：
[
  {\"index\": 1, \"title\": \"选题标题\", \"grade\": \"S\", \"line\": \"科学信任\", \"score\": \"92\", \"compliance\": \"🟢\", \"angle\": \"核心角度\", \"audience\": \"目标人群\", \"outline\": \"大纲摘要\", \"alt_titles\": [\"标题2\", \"标题3\"]},
  ...
]"

  "$CLAUDE_BIN" -p "$prompt" > "$TOPICS_MD" 2>>"$LOG_FILE"

  if [ $? -ne 0 ] || [ ! -s "$TOPICS_MD" ]; then
    die "Claude CLI 选题生成失败"
  fi

  # 提取JSON部分
  python3 -c "
import re, sys
content = open('$TOPICS_MD').read()
m = re.search(r'\`\`\`json\s*\n(.*?)\n\`\`\`', content, re.DOTALL)
if m:
    print(m.group(1))
else:
    # fallback: 尝试找最后一个JSON数组
    m = re.search(r'(\[[\s\S]*\])\s*$', content)
    if m:
        print(m.group(1))
    else:
        sys.exit(1)
" > "$TOPICS_JSON" 2>/dev/null

  if [ $? -ne 0 ] || [ ! -s "$TOPICS_JSON" ]; then
    log "WARNING: 无法提取JSON，将使用文本解析模式"
  else
    log "选题JSON已提取: $TOPICS_JSON"
  fi

  local count
  count=$(python3 -c "import json; print(len(json.load(open('$TOPICS_JSON'))))" 2>/dev/null || echo "0")
  log "STEP 1 完成: 生成 ${count} 个选题"
}

# ============================================================
# STEP 2: 创建飞书云文档
# ============================================================

create_feishu_doc() {
  log "STEP 2: 创建飞书云文档..."

  local token
  token=$(get_tenant_token) || die "获取飞书token失败"

  # 构建文档内容（Markdown风格）
  local doc_title="日生研NSKSD · ${TODAY} 选题方案"

  # 用Python构建文档body（飞书文档API需要特定的block结构）
  local doc_content
  doc_content=$(python3 << 'PYEOF'
import json, sys, os

topics_json = os.environ.get("TOPICS_JSON", "/tmp/nsksd-topics-today.json")
today = os.environ.get("TODAY", "2026-04-15")

try:
    with open(topics_json) as f:
        topics = json.load(f)
except:
    topics = []

# 构建纯文本内容（用于飞书文档）
lines = []
lines.append(f"日生研NSKSD · {today} 选题方案")
lines.append("=" * 40)
lines.append("")

grade_names = {"S": "S级（立即可写）", "A": "A级（值得写）", "B": "B级（备选）"}
for grade in ["S", "A", "B"]:
    group = [t for t in topics if t.get("grade") == grade]
    if not group:
        continue
    lines.append(f"\n{'='*20} {grade_names.get(grade, grade)} {'='*20}\n")
    for t in group:
        idx = t.get("index", "?")
        lines.append(f"选题 {idx}: {t.get('title', '')}")
        lines.append(f"  内容线: {t.get('line', '')}")
        lines.append(f"  核心角度: {t.get('angle', '')}")
        lines.append(f"  目标人群: {t.get('audience', '')}")
        lines.append(f"  合规分级: {t.get('compliance', '🟢')}")
        lines.append(f"  评分: {t.get('score', '')}分")
        if t.get("alt_titles"):
            lines.append(f"  备选标题:")
            for alt in t["alt_titles"]:
                lines.append(f"    - {alt}")
        if t.get("outline"):
            lines.append(f"  大纲: {t.get('outline', '')}")
        lines.append("")

print("\n".join(lines))
PYEOF
  )

  # 创建飞书文档
  local create_resp
  create_resp=$(curl -s -X POST "https://open.feishu.cn/open-apis/docx/v1/documents" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "{\"title\": \"$doc_title\"}")

  local doc_id
  doc_id=$(echo "$create_resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['document']['document_id'])" 2>/dev/null)

  if [ -z "$doc_id" ]; then
    log "WARNING: 创建飞书文档失败，跳过云文档步骤"
    log "API响应: $create_resp"
    echo "" > "$DOC_URL_FILE"
    return
  fi

  log "文档已创建: $doc_id"

  # 写入文档内容（逐个block）
  # 先获取文档的根block_id
  local doc_info
  doc_info=$(curl -s -X GET "https://open.feishu.cn/open-apis/docx/v1/documents/$doc_id" \
    -H "Authorization: Bearer $token")

  # 用Python批量构建blocks并写入
  python3 << PYEOF2
import json, os, sys
import urllib.request

token = "$token"
doc_id = "$doc_id"
topics_json = os.environ.get("TOPICS_JSON", "/tmp/nsksd-topics-today.json")
today = os.environ.get("TODAY", "2026-04-15")

try:
    with open(topics_json) as f:
        topics = json.load(f)
except:
    topics = []
    print("WARNING: 无法读取选题JSON", file=sys.stderr)

# 构建blocks
blocks = []

# 分级标题
grade_info = {"S": "S级 (立即可写)", "A": "A级 (值得写)", "B": "B级 (备选)"}

for grade in ["S", "A", "B"]:
    group = [t for t in topics if t.get("grade") == grade]
    if not group:
        continue

    # 分级标题
    blocks.append({
        "block_type": 4,  # heading2
        "heading2": {
            "elements": [{"text_run": {"content": grade_info[grade]}}]
        }
    })

    for t in group:
        # 选题标题
        blocks.append({
            "block_type": 5,  # heading3
            "heading3": {
                "elements": [{"text_run": {"content": f"{t.get('index', '?')}. {t.get('title', '')}"}}]
            }
        })

        # 详细信息
        info_lines = [
            f"内容线: {t.get('line', '')} | 合规: {t.get('compliance', '🟢')} | 评分: {t.get('score', '')}分",
            f"核心角度: {t.get('angle', '')}",
            f"目标人群: {t.get('audience', '')}",
        ]
        if t.get("outline"):
            info_lines.append(f"大纲: {t.get('outline', '')}")

        for line in info_lines:
            blocks.append({
                "block_type": 2,  # text
                "text": {
                    "elements": [{"text_run": {"content": line}}]
                }
            })

        # 备选标题
        if t.get("alt_titles"):
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": "备选标题:", "text_element_style": {"bold": True}}}]
                }
            })
            for alt in t["alt_titles"]:
                blocks.append({
                    "block_type": 16,  # bullet
                    "bullet": {
                        "elements": [{"text_run": {"content": alt}}]
                    }
                })

        # 分隔
        blocks.append({"block_type": 22})  # divider

# 批量创建blocks（每次最多50个）
for i in range(0, len(blocks), 50):
    batch = blocks[i:i+50]
    data = json.dumps({
        "children": batch,
        "index": -1
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.load(resp)
            if result.get("code") != 0:
                print(f"WARNING: 写入blocks失败: {result}", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: 写入blocks异常: {e}", file=sys.stderr)

print(f"文档内容写入完成，共 {len(blocks)} 个blocks")
PYEOF2

  # 设置文档权限（让曲率可以访问）
  curl -s -X POST "https://open.feishu.cn/open-apis/drive/v1/permissions/${doc_id}/members?type=docx" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "{
      \"member_type\": \"openid\",
      \"member_id\": \"$TARGET_OPEN_ID\",
      \"perm\": \"full_access\"
    }" > /dev/null 2>&1

  local doc_url="https://bytedance.feishu.cn/docx/$doc_id"
  echo "$doc_url" > "$DOC_URL_FILE"
  log "STEP 2 完成: $doc_url"
}

# ============================================================
# STEP 3: 推送飞书卡片
# ============================================================

send_topic_cards() {
  log "STEP 3: 推送飞书卡片（清单卡 + 多选卡）..."

  # 等监听服务就绪
  local retries=0
  while [ $retries -lt 10 ]; do
    if curl -s http://localhost:9800/health > /dev/null 2>&1; then
      break
    fi
    retries=$((retries + 1))
    sleep 2
  done

  if [ $retries -ge 10 ]; then
    die "监听服务未就绪，无法发送卡片"
  fi

  # 读取飞书云文档URL
  local doc_url=""
  if [ -f "$DOC_URL_FILE" ] && [ -s "$DOC_URL_FILE" ]; then
    doc_url=$(cat "$DOC_URL_FILE")
  fi

  # ---- 第一张：清单卡（选题概览 + 云文档链接） ----
  local resp1
  resp1=$(curl -s -X POST http://localhost:9800/send-summary-card \
    -H 'Content-Type: application/json' \
    -d "{\"doc_url\": \"$doc_url\"}")

  local code1
  code1=$(echo "$resp1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code', -1))" 2>/dev/null || echo "-1")

  if [ "$code1" = "0" ]; then
    log "清单卡已推送"
  else
    log "WARNING: 清单卡推送失败: $resp1"
  fi

  # 间隔1秒，避免飞书限流
  sleep 1

  # ---- 第二张：多选卡（勾选选题 → 触发写稿流程） ----
  local resp2
  resp2=$(curl -s -X POST http://localhost:9800/send-card \
    -H 'Content-Type: application/json' \
    -d '{}')

  local code2
  code2=$(echo "$resp2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code', -1))" 2>/dev/null || echo "-1")

  if [ "$code2" = "0" ]; then
    log "多选卡已推送"
  else
    log "WARNING: 多选卡推送失败: $resp2"
    die "多选卡推送失败"
  fi

  log "STEP 3 完成: 两张卡片已推送（清单卡 + 多选卡）"
}

# ============================================================
# STEP 4: 启动WSClient监听服务（等待用户回复编号）
# ============================================================

start_listener() {
  log "STEP 4: 启动监听服务..."

  if [ -z "$BUN_BIN" ]; then
    log "WARNING: bun 未找到，跳过监听服务启动"
    log "用户可以手动启动: cd $SERVER_DIR && bun run index.ts"
    return
  fi

  # 检查是否已在运行
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
    local register_data
    register_data=$(python3 -c "
import json
with open('$TOPICS_JSON') as f:
    topics = json.load(f)
payload = {'topics': topics}
print(json.dumps(payload, ensure_ascii=False))
" 2>/dev/null)

    if [ -n "$register_data" ]; then
      curl -s -X POST "http://localhost:9800/register-topics" \
        -H "Content-Type: application/json" \
        -d "$register_data" > /dev/null 2>&1 && \
        log "选题已注册到监听服务" || \
        log "WARNING: 注册选题失败，监听服务可能未就绪"
    fi
  fi

  log "STEP 4 完成"
}

# ============================================================
# 主流程
# ============================================================

main() {
  log "============================================"
  log "日生研NSKSD · 每日选题定时推送"
  log "日期: $TODAY"
  log "============================================"

  generate_topics
  create_feishu_doc
  start_listener       # 先启动监听服务（发卡片依赖它的HTTP端口）
  send_topic_cards     # 再通过监听服务发送多选卡片

  log "============================================"
  log "✅ 全部完成！"
  log "  选题文件: $TOPICS_MD"
  log "  选题JSON: $TOPICS_JSON"
  log "  运行日志: $LOG_FILE"
  log "  用户在飞书回复编号即可触发写稿+排版"
  log "============================================"
}

main "$@"
