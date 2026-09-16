#!/usr/bin/env bash
set -euo pipefail
readonly REVIEW_ROOT=/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
  -C "$REVIEW_ROOT" --add-dir /home/galbot/lizekai/RSI \
  --disable multi_agent --disable memories \
  -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
  resume --model gpt-6-astra --skip-git-repo-check --json \
  --output-last-message "$REVIEW_ROOT/memory-priority-last-message.md" \
  01a0a94d-6143-74c0-80cd-03d0b61acaf0 - \
  < "$REVIEW_ROOT/FOLLOWUP.md" 2>&1 | tee -a "$REVIEW_ROOT/memory-priority.log"
