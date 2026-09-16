#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
python3 tools/coordination/ikea_gate.py wait --physical-only 2>&1 | tee -a artifacts/R020/waiter.log
