#!/bin/bash
# 日生研内容创作 · Mac 启动飞书长连接监听器
# 用法:./run_listener_mac.sh [start|stop|status|logs]

set -e
cd "$(dirname "$0")"

VENV_DIR=".venv"
PID_FILE="listener.pid"
LOG_FILE="listener.out"

ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "[setup] 创建 venv..."
        python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/pip" install -q lark-oapi
    fi
}

cmd_start() {
    ensure_venv
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "[已在运行] PID=$(cat $PID_FILE)"
        exit 0
    fi
    nohup "$VENV_DIR/bin/python" lark_ws_listener.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 3
    echo "[启动] PID=$(cat $PID_FILE)"
    tail -5 "$LOG_FILE"
}

cmd_stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "[停止] PID=$PID"
        fi
        rm -f "$PID_FILE"
    else
        pkill -f "lark_ws_listener.py" 2>/dev/null || true
        echo "[停止] 兜底杀进程"
    fi
}

cmd_status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "[运行中] PID=$(cat $PID_FILE)"
    else
        echo "[未运行]"
    fi
}

cmd_logs() {
    tail -f "$LOG_FILE"
}

case "${1:-start}" in
    start) cmd_start ;;
    stop)  cmd_stop ;;
    status) cmd_status ;;
    logs)  cmd_logs ;;
    restart) cmd_stop; sleep 1; cmd_start ;;
    *) echo "用法:$0 [start|stop|status|logs|restart]"; exit 1 ;;
esac
