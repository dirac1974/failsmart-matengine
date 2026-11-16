#!/usr/bin/env bash
# Checks that a detached job keeps running inside WSL after you disconnect.
#
#   bash keepalive-test.sh start   # starts a 10-minute heartbeat in tmux; then log out completely
#   bash keepalive-test.sh check   # after logging back in: did it keep running?
#   bash keepalive-test.sh stop
set -euo pipefail

LOG="$HOME/keepalive.log"
SESSION="keepalive"
INTERVAL=15      # seconds between heartbeats
BEATS=40         # 40 x 15 s = 10 minutes

case "${1:-}" in
  start)
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    : > "$LOG"
    tmux new-session -d -s "$SESSION" \
      "for i in \$(seq 1 $BEATS); do date +%s >> '$LOG'; sleep $INTERVAL; done; echo done >> '$LOG'"
    echo "Heartbeat started. Now disconnect completely (exit Linux, exit SSH),"
    echo "wait at least 5 minutes, reconnect, and run:  bash keepalive-test.sh check"
    ;;
  check)
    [[ -s "$LOG" ]] || { echo "FAIL: no heartbeat log. Run 'start' first."; exit 1; }
    mapfile -t beats < <(grep -E '^[0-9]+$' "$LOG")
    n=${#beats[@]}
    max_gap=0
    for ((i = 1; i < n; i++)); do
      gap=$(( beats[i] - beats[i-1] ))
      (( gap > max_gap )) && max_gap=$gap
    done
    now=$(date +%s)
    since_last=$(( now - beats[n-1] ))
    finished=0; grep -q '^done$' "$LOG" && finished=1
    echo "heartbeats: $n   largest gap: ${max_gap}s   seconds since last: $since_last   finished: $finished"
    if (( max_gap > 3 * INTERVAL )); then
      echo "FAIL: the job was paused or the Linux VM was stopped while you were away."
      echo "      Check vmIdleTimeout in %USERPROFILE%\\.wslconfig on the Windows side, then 'wsl --shutdown' and retry."
      exit 1
    fi
    if (( finished == 0 && since_last > 3 * INTERVAL )); then
      echo "FAIL: the heartbeat stopped before finishing. The Linux VM was shut down."
      exit 1
    fi
    echo "PASS: the job kept running while you were disconnected."
    ;;
  stop)
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    echo "stopped"
    ;;
  *)
    echo "usage: bash keepalive-test.sh start|check|stop"; exit 2 ;;
esac
