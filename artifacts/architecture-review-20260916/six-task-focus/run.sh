#!/usr/bin/env bash
set -euo pipefail
readonly TASK_ROOT=/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916/six-task-focus
python3 - <<'CHECK'
import json
from pathlib import Path
p=Path('/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916/robot-stability-observation/engineer.jsonl')
assert json.loads(p.read_text().splitlines()[-1]).get('type')=='turn.completed'
CHECK
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
 -C "$TASK_ROOT" --add-dir /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
 -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
 resume --model gpt-6-astra --skip-git-repo-check --json \
 --output-last-message "$TASK_ROOT/last-message.md" 01a0a94d-6143-74c0-80cd-03d0b61acaf0 - \
 < "$TASK_ROOT/TASK.md" 2>&1 | tee -a "$TASK_ROOT/engineer.jsonl"
