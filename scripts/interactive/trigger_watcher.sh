#!/bin/bash
# ============================================================
# 日生研NSKSD · trigger 文件轮询器(v4 撰写流水线入口)
#
# listener 收到多选卡提交后,会在 triggers/ 目录写一份 JSON:
#   triggers/<session_id>.trigger
# 本脚本每 5s 扫描一次,发现新 trigger 就:
#   1. 打标 status=running
#   2. 调 claude -p 按 SKILL.md 跑完整撰写流水线
#   3. 成功后 mv 到 triggers/done/, 失败 mv 到 triggers/failed/
#   4. 通过飞书卡片回报状态(调 notify_trigger.py)
#
# 启动:
#   nohup bash trigger_watcher.sh > /tmp/nsksd-trigger-watcher.log 2>&1 &
#
# 手动测试单个 trigger:
#   bash trigger_watcher.sh --run /path/to/xxx.trigger
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
TRIGGERS_DIR="$SCRIPT_DIR/triggers"
DONE_DIR="$TRIGGERS_DIR/done"
FAILED_DIR="$TRIGGERS_DIR/failed"
LOG_DIR="$SKILL_DIR/logs"

mkdir -p "$TRIGGERS_DIR" "$DONE_DIR" "$FAILED_DIR" "$LOG_DIR"

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
[ -n "$CLAUDE_BIN" ] || { echo "[FATAL] claude CLI 未找到"; exit 1; }

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

process_trigger() {
  local trigger_file="$1"
  local session_id
  session_id=$(python3 -c "import json,sys; print(json.load(open('$trigger_file'))['session_id'])")
  local work_log="$LOG_DIR/writing-$session_id.log"

  log "→ 处理 trigger: $(basename "$trigger_file") (session=$session_id)"

  # 标记 running
  python3 -c "
import json, datetime
p = '$trigger_file'
d = json.load(open(p))
d['status'] = 'running'
d['started_at'] = datetime.datetime.now().isoformat(timespec='seconds')
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
"

  # 读取选题标题 + chat_id,供 Claude CLI 跑
  local chosen_titles chosen_ids open_chat_id
  chosen_titles=$(python3 -c "import json; d=json.load(open('$trigger_file')); print('\n'.join(f'- {t}' for t in d['chosen_titles']))")
  chosen_ids=$(python3 -c "import json; d=json.load(open('$trigger_file')); print(','.join(d['chosen_ids']))")
  open_chat_id=$(python3 -c "import json; d=json.load(open('$trigger_file')); print(d.get('open_chat_id',''))")

  # 调 Claude CLI 跑流水线(按 SKILL.md 要求)
  local prompt
  prompt=$(cat <<EOF
你是日生研 NSKSD 内容撰写流水线,请按 $SKILL_DIR/SKILL.md 执行以下选题的完整撰写:

【本次撰写的选题】
$chosen_titles

【会话信息】
- session_id: $session_id
- chosen_ids: $chosen_ids
- open_chat_id: $open_chat_id

【强制流水线 5 步】
1. title-outliner: 按 references/title-playbook.md 出 3 个备选标题 + 大纲
2. article-writer: 按 references/nsksd-writing-style.md 出正文（大白话+专业，不引个人风格）
3. quyu-view-checker: 扫描禁用词/句式,不过退回重写
4. image-designer: 走 xhs-image-creator Bento Grid 风格配图
5. format-publisher: 排版（nsksd_publish 本地流水线），结果写 /tmp/nsksd-publish-${session_id}.result

【完成后动作】
每篇完成,调:
  python3 $SCRIPT_DIR/send_notify.py --chat-id "$open_chat_id" --kind done --title "<标题>" --draft-url "<公众号草稿链接>"

全部完成后,调:
  python3 $SCRIPT_DIR/send_notify.py --chat-id "$open_chat_id" --kind all_done --count <篇数>

【失败时】
  python3 $SCRIPT_DIR/send_notify.py --chat-id "$open_chat_id" --kind failed --reason "<错误原因>"

严格遵循 SKILL.md V9.4 规范,不要跳步。
EOF
)

  log "  调用 claude -p 跑流水线（Steps 1-4）..."
  if "$CLAUDE_BIN" -p "$prompt" > "$work_log" 2>&1; then
    log "  ✅ Steps 1-4 完成，执行 Step 5: 发布"

    # Step 5: 发布（nsksd_publish 本地流水线）
    local HTML_FILE="/tmp/nsksd-article-${session_id}.html"
    local COVER_FILE="/tmp/nsksd-cover-${session_id}.jpg"
    local ARTICLE_TITLE
    ARTICLE_TITLE=$(python3 -c "
import json, sys
d = json.load(open('$trigger_file'))
titles = d.get('chosen_titles', [])
print(titles[0] if titles else 'NSKSD文章')
" 2>/dev/null || echo "NSKSD文章")

    log "Step 5: 发布（nsksd_publish 本地流水线）"
    python3 "$SKILL_DIR/scripts/nsksd_publish.py" \
      --html "$HTML_FILE" \
      --cover "$COVER_FILE" \
      --title "$ARTICLE_TITLE" \
      --session-id "$session_id" \
      >> "$work_log" 2>&1
    PUBLISH_EXIT=$?
    case $PUBLISH_EXIT in
      0) log "✅ 公众号推送成功" ;;
      3) log "⚠️ 凭证缺失，已走飞书云文档保底" ;;
      4) log "⚠️ 公众号推送失败，已走飞书云文档保底" ;;
      *) log "❌ 发布异常 exit=$PUBLISH_EXIT" ;;
    esac
    python3 -c "
import json, datetime
p = '$trigger_file'
d = json.load(open(p))
d['status'] = 'done'
d['finished_at'] = datetime.datetime.now().isoformat(timespec='seconds')
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
"
    mv "$trigger_file" "$DONE_DIR/"
  else
    log "  ❌ 流水线失败,日志: $work_log"
    python3 -c "
import json, datetime
p = '$trigger_file'
d = json.load(open(p))
d['status'] = 'failed'
d['finished_at'] = datetime.datetime.now().isoformat(timespec='seconds')
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
"
    mv "$trigger_file" "$FAILED_DIR/"
    # 调通知
    python3 "$SCRIPT_DIR/send_notify.py" --chat-id "$open_chat_id" --kind failed \
      --reason "流水线失败,日志见 $work_log" 2>/dev/null || true
  fi
}

# 模式 1: 处理单个 trigger(测试用)
if [ "${1:-}" = "--run" ] && [ -n "${2:-}" ]; then
  process_trigger "$2"
  exit 0
fi

# 模式 2: 守护进程,每 5s 扫一次
log "🔄 trigger-watcher 启动,监听 $TRIGGERS_DIR/*.trigger"
while true; do
  shopt -s nullglob
  for f in "$TRIGGERS_DIR"/*.trigger; do
    # 只处理 status=pending 的(避免重复跑)
    status=$(python3 -c "import json; print(json.load(open('$f')).get('status','pending'))" 2>/dev/null || echo "unknown")
    if [ "$status" = "pending" ]; then
      process_trigger "$f" || log "  [WARN] process_trigger 异常,继续"
    fi
  done
  sleep 5
done
