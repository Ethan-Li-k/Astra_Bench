#!/usr/bin/env bash
set -euo pipefail
RECOVERY=/home/galbot/lizekai/RSI/api-ground-to-table/recovery-20260916
ADAPTER=/home/galbot/lizekai/RSI/api-ground-to-table/actor-adapter
export CODEX_HOME=/home/galbot/lizekai/RSI/codex-account-2/home
export CODEX_THREAD_ID=01a0a982-cec5-71c0-b771-091c31df61f2
export PYTHONDONTWRITEBYTECODE=1
cd "$ADAPTER"
test ! -e "$ADAPTER/campaign/episode-0003"
test ! -e "$RECOVERY/run-003.log"
test ! -e "$RECOVERY/run-003.started"
python "$RECOVERY/verify_ready.py"
date --iso-8601=seconds > "$RECOVERY/run-003.started"
set +e
bash "$ADAPTER/run.sh" --run-id api-ground-003 --episode episode-0003 \
  --authorization "$ADAPTER/authorization-003.json" \
  --budget-hook "$RECOVERY/recovery_budget.py" 2>&1 | tee "$RECOVERY/run-003.log"
run_exit=${PIPESTATUS[0]}
set -e
printf '%s\n' "$run_exit" > "$RECOVERY/run-003.exit-code"
exit "$run_exit"
