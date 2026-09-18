#!/usr/bin/env bash
# Source this file on psi_being to enter the isolated SIMPLE/Isaac environment.
# Runtime caches and user files stay under the RSI project directory.

_SIMPLE_BASE=/home/galbot/lizekai/RSI/simple-isaac-20260917
export SIMPLE_ROOT="$_SIMPLE_BASE/SIMPLE"
export VIRTUAL_ENV="$SIMPLE_ROOT/.venv"
export HOME="$_SIMPLE_BASE/home"
export XDG_CACHE_HOME="$_SIMPLE_BASE/cache/xdg"
export XDG_CONFIG_HOME="$_SIMPLE_BASE/config"
export XDG_DATA_HOME="$_SIMPLE_BASE/data/xdg"
export UV_CACHE_DIR="$_SIMPLE_BASE/cache/uv"
export CUDA_HOME=/usr/local/cuda
export TORCH_CUDA_ARCH_LIST=8.9+PTX
export MUJOCO_GL=egl
export OMNI_KIT_ACCEPT_EULA=Y
export PYTHONNOUSERSITE=1

unset PYTHONPATH CONDA_PREFIX CONDA_DEFAULT_ENV
unset LD_LIBRARY_PATH
export PATH="$VIRTUAL_ENV/bin:$_SIMPLE_BASE/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin"
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
hash -r
cd "$SIMPLE_ROOT"
unset _SIMPLE_BASE
