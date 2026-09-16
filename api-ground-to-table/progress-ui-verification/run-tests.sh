#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
{
  python3 -m unittest discover -s human-feedback/tools -p test_video_home.py -v
  python3 -m unittest discover -s human-feedback/tools -p test_api_progress.py -v
  node --check human-feedback/ui/app.js
} 2>&1 | tee -a api-ground-to-table/progress-ui-verification/tests.log
