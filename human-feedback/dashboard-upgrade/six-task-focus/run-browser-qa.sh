#!/bin/bash
set -o pipefail
cd /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/six-task-focus
node browser-check.mjs 2>&1 | tee browser-qa.log
printf '%s\n' "${PIPESTATUS[0]}" > browser-qa.exit
