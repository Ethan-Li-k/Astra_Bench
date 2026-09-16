#!/usr/bin/env bash
set -euo pipefail
readonly TASK_ROOT=/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916/no-truncation
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
 -C "$TASK_ROOT" --add-dir /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
 -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
 resume --model gpt-6-astra --skip-git-repo-check --json \
 --output-last-message "$TASK_ROOT/last-message.md" 01a0a94d-6143-74c0-80cd-03d0b61acaf0 - \
 < "$TASK_ROOT/TASK.md" 2>&1 | tee -a "$TASK_ROOT/engineer.jsonl"
