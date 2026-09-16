#!/usr/bin/env bash
set -euo pipefail
readonly TASK_ROOT=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/explicit-blockers
python3 - <<'CHECK'
import json
from pathlib import Path
p=Path('/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/attempted-catalog/engineer.jsonl')
assert json.loads(p.read_text().splitlines()[-1]).get('type')=='turn.completed'
CHECK
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
 -C "$TASK_ROOT" --add-dir /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
 -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
 resume --model gpt-6-astra --skip-git-repo-check --json \
 --output-last-message "$TASK_ROOT/last-message.md" 01a0a980-7943-7963-9f36-b9c43c90c2da - \
 < "$TASK_ROOT/TASK.md" 2>&1 | tee -a "$TASK_ROOT/engineer.jsonl"
