#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/galbot/lizekai/RSI TMPDIR=/home/galbot/lizekai/RSI/artifacts/R018/tmp
/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python artifacts/R019/recovery-20260916/check_permission_contract.py 2>&1 | tee artifacts/R019/recovery-20260916/permission-handshake.log
