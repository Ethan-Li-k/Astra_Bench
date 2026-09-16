#!/usr/bin/env bash
set -uo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/experiments/H001
export TMPDIR="$PWD/tmp" PYTHONDONTWRITEBYTECODE=1
/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python assess_trial.py "$1" 2>&1 | tee "logs/assess-$1.log"
result=${PIPESTATUS[0]}
printf '%s\n' "$result" > "logs/assess-$1.exit"
exit "$result"
