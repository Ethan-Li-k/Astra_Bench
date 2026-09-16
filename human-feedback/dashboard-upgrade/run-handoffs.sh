#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade
export PYTHONDONTWRITEBYTECODE=1
python3 send-owner-handoffs.py 2>&1 | tee -a handoffs.log
