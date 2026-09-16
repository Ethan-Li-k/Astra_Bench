#!/usr/bin/env bash
set -euo pipefail
umask 077

TASK_ROOT=/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table
mkdir -p "$TASK_ROOT/logs" "$TASK_ROOT/tmp" "$TASK_ROOT/cache"
cd "$TASK_ROOT"
export TMPDIR="$TASK_ROOT/tmp"
export XDG_CACHE_HOME="$TASK_ROOT/cache"
export PYTHONDONTWRITEBYTECODE=1

/home/galbot/lizekai/RSI/codex-account-2/run.sh exec \
  --json --approve-for-me --skip-git-repo-check \
  -C "$TASK_ROOT" --model gpt-6-astra \
  -c 'model_reasoning_effort="xhigh"' -c 'model_provider="openai"' \
  --disable multi_agent --disable memories \
  --output-last-message "$TASK_ROOT/RESULT.md" \
  - < "$TASK_ROOT/TASK.md" 2>&1 | tee -a "$TASK_ROOT/logs/supervisor.jsonl"
