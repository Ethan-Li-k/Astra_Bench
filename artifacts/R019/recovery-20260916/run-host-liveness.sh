#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/R019/recovery-20260916/check_host_liveness.py 2>&1 | tee artifacts/R019/recovery-20260916/host-liveness-check.log
