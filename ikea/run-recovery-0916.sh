#!/usr/bin/env bash
set -euo pipefail
readonly IKEA_ROOT=/home/galbot/lizekai/RSI/ikea
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$IKEA_ROOT/tmp" XDG_CACHE_HOME="$IKEA_ROOT/cache"
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
  -C "$IKEA_ROOT" --add-dir /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
  -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
  resume --model gpt-6-astra --skip-git-repo-check --json \
  --output-last-message "$IKEA_ROOT/recovery-20260916/last-message.md" \
  01a0a96b-06cc-7150-8c73-7b0897936b52 - \
  < "$IKEA_ROOT/RECOVERY-20260916.md" 2>&1 | tee -a "$IKEA_ROOT/recovery-20260916/engineer.jsonl"
