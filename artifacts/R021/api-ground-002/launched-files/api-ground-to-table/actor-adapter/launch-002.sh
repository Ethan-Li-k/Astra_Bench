#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/galbot/lizekai/RSI/api-ground-to-table/actor-adapter
cd "$ROOT"
test ! -e "$ROOT/campaign/episode-0002"
test ! -e "$ROOT/run-002.log"
set +e
bash "$ROOT/run.sh" --run-id api-ground-002 --episode episode-0002 \
  --authorization "$ROOT/authorization-002.json" 2>&1 | tee "$ROOT/run-002.log"
exit_code=${PIPESTATUS[0]}
set -e
printf '%s\n' "$exit_code" > "$ROOT/run-002.exit-code"
exit "$exit_code"
