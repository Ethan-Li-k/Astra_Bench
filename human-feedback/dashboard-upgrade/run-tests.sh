#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
{ python3 -m unittest discover -s human-feedback/tools -p 'test_*.py' -v; node --check human-feedback/ui/app.js; } 2>&1 | tee -a human-feedback/dashboard-upgrade/tests.log
