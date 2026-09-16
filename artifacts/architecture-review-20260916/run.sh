#!/usr/bin/env bash
set -euo pipefail
readonly REVIEW_ROOT=/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
  -C "$REVIEW_ROOT" --add-dir /home/galbot/lizekai/RSI \
  --disable multi_agent --disable memories \
  -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
  --model gpt-6-astra --skip-git-repo-check --json \
  --output-last-message "$REVIEW_ROOT/last-message.md" - \
  < "$REVIEW_ROOT/TASK.md" 2>&1 | tee -a "$REVIEW_ROOT/review.log"
