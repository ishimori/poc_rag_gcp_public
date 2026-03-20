#!/usr/bin/env bash
# ポート 5180, 8081 を使用中のプロセスを強制終了する
#
# 使い方:
#   bash scripts/dev-kill.sh

cd "$(dirname "$0")/.."

API_PORT="${API_PORT:-8081}"
UI_PORT="${UI_PORT:-5180}"
killed=0

for port in "$API_PORT" "$UI_PORT"; do
  pids=$(netstat -ano 2>/dev/null | grep "LISTENING" | grep ":${port} " | awk '{print $5}' | sort -u)
  for pid in $pids; do
    if [ -n "$pid" ] && [ "$pid" != "0" ]; then
      taskkill //F //PID "$pid" 2>/dev/null && echo "Killed PID $pid (port $port)" && killed=$((killed + 1))
    fi
  done
done

rm -f .dev-pids

if [ "$killed" -eq 0 ]; then
  echo "No processes found on ports $API_PORT, $UI_PORT."
else
  echo "Done. Killed $killed process(es)."
fi
