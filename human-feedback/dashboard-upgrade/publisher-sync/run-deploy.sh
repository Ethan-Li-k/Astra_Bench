#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
PYTHONDONTWRITEBYTECODE=1 python3 human-feedback/dashboard-upgrade/publisher-sync/restart-ui.py 2>&1 | tee human-feedback/dashboard-upgrade/publisher-sync/deploy.log
