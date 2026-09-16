#!/bin/bash
set -euo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/explicit-blockers
export TMPDIR=tmp
mkdir -p "$TMPDIR"
google-chrome --enable-logging=stderr --headless=new --disable-gpu --disable-background-networking --disable-component-update --no-first-run --no-default-browser-check --remote-debugging-address=127.0.0.1 --remote-debugging-port=0 --user-data-dir="$PWD/browser-profile" about:blank 2>&1 | tee -a browser.log
