#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/galbot/lizekai/RSI/human-feedback/tools:/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/attempted-catalog
python3 -m unittest -v test_attempted_catalog 2>&1 | tee human-feedback/dashboard-upgrade/attempted-catalog/tests.log
