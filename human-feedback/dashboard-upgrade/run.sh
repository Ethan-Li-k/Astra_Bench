#!/usr/bin/env bash
set -euo pipefail
readonly TASK_ROOT=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
 -C "$TASK_ROOT" --add-dir /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
 -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
 --model gpt-6-astra --skip-git-repo-check --json \
 --output-last-message "$TASK_ROOT/last-message.md" - \
 < "$TASK_ROOT/TASK.md" 2>&1 | tee -a "$TASK_ROOT/engineer.jsonl"
