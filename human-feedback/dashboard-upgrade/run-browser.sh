#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export TMPDIR=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/tmp
mkdir -p "$TMPDIR"
google-chrome --headless=new --disable-gpu --disable-background-networking --disable-component-update --no-first-run --no-default-browser-check --remote-debugging-address=127.0.0.1 --remote-debugging-port=0 --user-data-dir=/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/browser-profile about:blank 2>&1 | tee -a human-feedback/dashboard-upgrade/browser.log
