#!/bin/bash
set -o pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/galbot/lizekai/RSI/human-feedback/tools
out=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/six-task-focus
python3 "$out/test_six_task_focus.py" 2>&1 | tee "$out/tests-$1.log"
printf '%s\n' "${PIPESTATUS[0]}" > "$out/tests-$1.exit"
