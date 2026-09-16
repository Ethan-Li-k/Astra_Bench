#!/usr/bin/env bash
set -euo pipefail
umask 077
REVIEW_ROOT=/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table/reviewer
mkdir -p "$REVIEW_ROOT/tmp" "$REVIEW_ROOT/cache"
cd "$REVIEW_ROOT"
export TMPDIR="$REVIEW_ROOT/tmp"
export XDG_CACHE_HOME="$REVIEW_ROOT/cache"
export PYTHONDONTWRITEBYTECODE=1
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec \
  --json --approve-for-me --skip-git-repo-check \
  -C "$REVIEW_ROOT" --model gpt-6-astra \
  -c 'model_reasoning_effort="xhigh"' -c 'model_provider="openai"' \
  --disable multi_agent --disable memories \
  --output-last-message "$REVIEW_ROOT/FINAL.md" \
  - < "$REVIEW_ROOT/TASK.md" 2>&1 | tee -a "$REVIEW_ROOT/events.jsonl"
