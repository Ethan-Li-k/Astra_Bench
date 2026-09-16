#!/usr/bin/env bash
set -uo pipefail
cd /home/galbot/lizekai/RSI/human-feedback/reproductions/H001
export TMPDIR="$PWD/tmp"
export XDG_CACHE_HOME="$PWD/cache"
export MPLCONFIGDIR="$PWD/cache/matplotlib"
export CUDA_CACHE_PATH="$PWD/cache/cuda"
export __GL_SHADER_DISK_CACHE_PATH="$PWD/cache/gl"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export MUJOCO_GL=egl
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONPATH="$PWD/host_audit/runtime:/home/galbot/lizekai/Loco_manip/locomanip/src"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$MPLCONFIGDIR" "$CUDA_CACHE_PATH" "$__GL_SHADER_DISK_CACHE_PATH"
/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python reproduce.py attempt-002 2>&1 | tee logs/physics-attempt-002.log
result=${PIPESTATUS[0]}
printf '%s\n' "$result" > logs/physics-attempt-002.exit
exit "$result"
