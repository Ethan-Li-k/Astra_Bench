#!/bin/bash
set -o pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/galbot/lizekai/RSI/human-feedback/tools
out=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/explicit-blockers
python3 "$out/test_explicit_blockers.py" 2>&1 | tee "$out/tests-$1.log"
printf '%s\n' "${PIPESTATUS[0]}" > "$out/tests-$1.exit"
