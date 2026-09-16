#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
node human-feedback/dashboard-upgrade/publisher-sync/browser-check.mjs 2>&1 | tee human-feedback/dashboard-upgrade/publisher-sync/browser-check.log
