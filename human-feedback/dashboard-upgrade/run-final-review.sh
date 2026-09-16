#!/usr/bin/env bash
set -euo pipefail
readonly TASK_ROOT=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade
python3 - <<'CHECK'
import json
from pathlib import Path
p=Path('/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/engineer.jsonl')
events=[json.loads(s) for s in p.read_text().splitlines() if s.strip().startswith('{')]
assert events[-1].get('type') == 'turn.completed', 'Previous full turn is not completed; do not resume concurrently'
p2=Path('/home/galbot/lizekai/RSI/ikea/web-progress-verification/targeted-fix.jsonl')
if p2.exists():
    last=json.loads(p2.read_text().splitlines()[-1])
    assert last.get('type') == 'turn.completed', 'IKEA UI fix is still active; do not resume concurrently'
CHECK
/home/galbot/lizekai/RSI/codex-account-2/run.sh exec --approve-for-me \
 -C "$TASK_ROOT" --add-dir /home/galbot/lizekai/RSI --disable multi_agent --disable memories \
 -c 'model_provider="openai"' -c 'model_reasoning_effort="xhigh"' \
 resume --model gpt-6-astra --skip-git-repo-check --json \
 --output-last-message "$TASK_ROOT/final-review-last-message.md" \
 01a0a980-7943-7963-9f36-b9c43c90c2da - \
 < "$TASK_ROOT/ROOT_FINAL_REVIEW.md" 2>&1 | tee -a "$TASK_ROOT/final-review-engineer.jsonl"
