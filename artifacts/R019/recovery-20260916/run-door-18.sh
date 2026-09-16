#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export TMPDIR=/home/galbot/lizekai/RSI/artifacts/R018/tmp
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MUJOCO_GL=egl
export PYTHONPATH=/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src
/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python tools/learn_door_skill.py --pd-profile checkpoint --continuous-chunks --door-frame-override --output artifacts/R019/door-campaign 2>&1 | tee artifacts/R019/door-campaign-18-recovery.log
