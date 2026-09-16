#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
exec google-chrome --headless=new --disable-gpu --disable-background-networking --disable-component-update --no-first-run --no-default-browser-check --remote-debugging-address=127.0.0.1 --remote-debugging-port=0 --user-data-dir=/home/galbot/lizekai/RSI/human-feedback/reviews/browser-profile about:blank 2>&1 | tee -a human-feedback/reviews/browser.log
