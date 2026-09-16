#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade
python3 restart-ui.py 2>&1 | tee -a restart.log
