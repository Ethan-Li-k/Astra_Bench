#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MUJOCO_GL=egl
export TMPDIR=/home/galbot/lizekai/RSI/ikea/tmp
export XDG_CACHE_HOME=/home/galbot/lizekai/RSI/ikea/cache
export MPLCONFIGDIR=$XDG_CACHE_HOME/matplotlib
export TORCH_HOME=$XDG_CACHE_HOME/torch CUDA_CACHE_PATH=$XDG_CACHE_HOME/cuda
export __GL_SHADER_DISK_CACHE_PATH=$XDG_CACHE_HOME/gl MESA_SHADER_CACHE_DIR=$XDG_CACHE_HOME/mesa
export PYTHONPATH=/home/galbot/lizekai/RSI/ikea:/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src
exec /home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python "$@"
