#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
node human-feedback/dashboard-upgrade/ikea-label-fix/browser-check.mjs 2>&1 | tee -a human-feedback/dashboard-upgrade/ikea-label-fix/browser-check.log
