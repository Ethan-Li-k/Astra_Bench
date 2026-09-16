#!/usr/bin/env bash
set -uo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/reproductions/H001
export TMPDIR="$PWD/tmp"
export XDG_CACHE_HOME="$PWD/cache"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python analyze.py 2>&1 | tee host_audit/analysis.log
result=${PIPESTATUS[0]}
printf '%s\n' "$result" > logs/analysis.exit
exit "$result"
