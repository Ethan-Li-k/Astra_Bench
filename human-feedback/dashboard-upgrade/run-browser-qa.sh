#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade
DASHBOARD_FIXTURE_PORT=8768 node browser-qa.mjs 2>&1 | tee -a browser-qa.log
