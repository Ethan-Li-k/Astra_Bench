#!/usr/bin/env bash
set -euo pipefail
readonly IKEA_ROOT=/home/galbot/lizekai/RSI/ikea
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
  -C /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
  -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
  resume --model gpt-6-astra --skip-git-repo-check --json \
  --output-last-message "$IKEA_ROOT/budget-coordination/recovery-last-message.md" \
  01a0a87f-f806-7883-9648-190e49447d86 - \
  < "$IKEA_ROOT/BUDGET_RECOVERY-20260916.md" 2>&1 | tee -a "$IKEA_ROOT/budget-coordination/recovery-engineer.jsonl"
