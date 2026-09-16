#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI/artifacts/R019/nt-audit-integration-20260916
export TMPDIR=/home/galbot/lizekai/RSI/artifacts/R018/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH=/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src
py=/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python
"$py" -B tests/test_joint.py 2>&1 | tee joint-tests.log
"$py" -B tests/test_budget.py 2>&1 | tee budget-tests.log
"$py" -B tests/run_regressions.py 2>&1 | tee regressions.log
