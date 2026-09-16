#!/bin/bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export TMPDIR=/home/galbot/lizekai/RSI/artifacts/R018/tmp
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
  -C /home/galbot/lizekai/RSI/codex-account-2/workspace --add-dir /home/galbot/lizekai/RSI \
  --disable multi_agent --disable memories \
  -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
  resume --json --skip-git-repo-check --model gpt-6-astra \
  --output-last-message /home/galbot/lizekai/RSI/artifacts/R019/r020-frame-review-final.md \
  01a0a87f-f806-7883-9648-190e49447d86 - \
  < /home/galbot/lizekai/RSI/artifacts/R019/r020-frame-review-followup.md \
  2>&1 | tee /home/galbot/lizekai/RSI/artifacts/R019/r020-frame-review-followup.jsonl
