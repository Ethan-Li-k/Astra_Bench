#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
PYTHONDONTWRITEBYTECODE=1 python3 ikea/budget-coordination/tests/run_suite.py 2>&1 | tee ikea/budget-coordination/tests/candidate-tests.log
