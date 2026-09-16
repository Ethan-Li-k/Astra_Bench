#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
node human-feedback/dashboard-upgrade/root-review/browser-check.mjs 2>&1 | tee human-feedback/dashboard-upgrade/root-review/browser-check.log
