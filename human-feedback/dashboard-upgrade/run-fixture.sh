#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
python3 human-feedback/tools/server.py --port 8766 --fixture-root /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/fixture-browser 2>&1 | tee -a human-feedback/dashboard-upgrade/fixture-server.log
