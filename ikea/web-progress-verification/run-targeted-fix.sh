#!/usr/bin/env bash
set -euo pipefail
readonly REVIEW_ROOT=/home/galbot/lizekai/RSI/ikea/web-progress-verification
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
  -C /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
  -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
  resume --model gpt-6-astra --skip-git-repo-check --json \
  --output-last-message "$REVIEW_ROOT/targeted-fix-final.md" \
  01a0a980-7943-7963-9f36-b9c43c90c2da - \
  < "$REVIEW_ROOT/TARGETED-UI-FIX.md" 2>&1 | tee -a "$REVIEW_ROOT/targeted-fix.jsonl"
