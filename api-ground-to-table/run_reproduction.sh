#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=/home/galbot/lizekai/RSI/api-ground-to-table
mkdir -p "$TASK_ROOT/tmp" "$TASK_ROOT/cache"
export TMPDIR="$TASK_ROOT/tmp" XDG_CACHE_HOME="$TASK_ROOT/cache" MPLCONFIGDIR="$TASK_ROOT/cache/matplotlib"
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/home/galbot/lizekai/Loco_manip/locomanip/src
cd "$TASK_ROOT"
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -u reproduce_f001.py
