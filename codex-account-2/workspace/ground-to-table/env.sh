#!/usr/bin/env bash
set -euo pipefail
export TASK_ROOT=/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table
export TMPDIR="$TASK_ROOT/tmp"
export XDG_CACHE_HOME="$TASK_ROOT/cache"
export MPLCONFIGDIR="$TASK_ROOT/cache/matplotlib"
export CUDA_CACHE_PATH="$TASK_ROOT/cache/cuda"
export __GL_SHADER_DISK_CACHE_PATH="$TASK_ROOT/cache/nvidia"
export MESA_SHADER_CACHE_DIR="$TASK_ROOT/cache/mesa"
export TORCH_HOME="$TASK_ROOT/cache/torch"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$TASK_ROOT:/home/galbot/lizekai/Loco_manip/locomanip/src"
export MUJOCO_GL=egl
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export TASK_PYTHON=/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python
cd "$TASK_ROOT"
