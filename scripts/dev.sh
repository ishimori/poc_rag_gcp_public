#!/usr/bin/env bash
# 開発サーバー起動スクリプト
# バックエンド（Cloud Functions）とフロントエンド（Vite）を同時起動
#
# 使い方:
#   bash scripts/dev.sh        # 起動
#   bash scripts/dev.sh stop   # 停止

set -euo pipefail
cd "$(dirname "$0")/.."

PIDFILE=".dev-pids"
API_PORT="${API_PORT:-8081}"
ADMIN_PORT="${ADMIN_PORT:-8082}"
UI_PORT="${UI_PORT:-5180}"

stop() {
  if [ -f "$PIDFILE" ]; then
    while read -r pid; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null && echo "Stopped PID $pid"
      fi
    done < "$PIDFILE"
    rm -f "$PIDFILE"
  fi
  # PIDファイルで漏れた子プロセスも確実に停止
  for port in $API_PORT $ADMIN_PORT; do
    pid=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
      kill -9 $pid 2>/dev/null && echo "Force killed process on port $port"
    fi
  done
  echo "All services stopped."
}

start() {
  # 既に起動中なら停止
  if [ -f "$PIDFILE" ]; then
    echo "Stopping existing services..."
    stop
  fi

  echo "Starting chat backend (port $API_PORT)..."
  uv run functions-framework --target=chat --port="$API_PORT" --source=main.py &
  API_PID=$!

  echo "Starting admin backend (port $ADMIN_PORT)..."
  uv run functions-framework --target=admin --port="$ADMIN_PORT" --source=main.py &
  ADMIN_PID=$!

  echo "Starting frontend (port $UI_PORT)..."
  cd ui && npm run dev -- --port "$UI_PORT" &
  UI_PID=$!
  cd ..

  echo "$API_PID" > "$PIDFILE"
  echo "$ADMIN_PID" >> "$PIDFILE"
  echo "$UI_PID" >> "$PIDFILE"

  echo ""
  echo "=== Dev servers running ==="
  echo "  Frontend: http://localhost:$UI_PORT"
  echo "  Chat API: http://localhost:$API_PORT"
  echo "  Admin API: http://localhost:$ADMIN_PORT"
  echo ""
  echo "Stop with: bash scripts/dev.sh stop"
  echo "==========================="

  # Ctrl+C で両方停止
  trap 'stop; exit 0' INT TERM
  wait
}

case "${1:-start}" in
  stop) stop ;;
  restart) stop; start ;;
  start|*) start ;;
esac
