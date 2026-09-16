#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI/api-ground-to-table
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/cache" PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$PWD/cache/matplotlib" CUDA_CACHE_PATH="$PWD/cache/cuda"
export __GL_SHADER_DISK_CACHE_PATH="$PWD/cache/nvidia" MESA_SHADER_CACHE_DIR="$PWD/cache/mesa"
export TORCH_HOME="$PWD/cache/torch" MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/home/galbot/lizekai/Loco_manip/locomanip/src
exec /home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python transfer_locomotion.py
