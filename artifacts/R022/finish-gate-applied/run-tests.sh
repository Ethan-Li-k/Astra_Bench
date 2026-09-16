#!/usr/bin/env bash
set -uo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/home/galbot/lizekai/RSI/artifacts/R022/finish-gate-applied/tmp
export XDG_CACHE_HOME=/home/galbot/lizekai/RSI/artifacts/R022/finish-gate-applied/cache
export MPLCONFIGDIR=/home/galbot/lizekai/RSI/artifacts/R022/finish-gate-applied/cache/matplotlib
export PYTHONPATH=/home/galbot/lizekai/RSI/tests:/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -B artifacts/R022/finish-gate-applied/run_tests.py 2>&1 | tee artifacts/R022/finish-gate-applied/logs/04-tests.log
test_status=${PIPESTATUS[0]}
printf '%s\n' "$test_status" > artifacts/R022/finish-gate-applied/tests-exit-code.txt
exit "$test_status"
