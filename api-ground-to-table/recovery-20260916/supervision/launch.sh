#!/usr/bin/env bash
set -euo pipefail
GROUND_WATCH=/home/galbot/lizekai/RSI/api-ground-to-table/recovery-20260916/supervision
export CODEX_HOME=/home/galbot/lizekai/RSI/codex-account-2/home
export CODEX_THREAD_ID=01a0a982-cec5-71c0-b771-091c31df61f2
export PYTHONDONTWRITEBYTECODE=1
test ! -e "$GROUND_WATCH/watch.log"
cd "$GROUND_WATCH"
python3 -u watch.py 2>&1 | tee watch.log
