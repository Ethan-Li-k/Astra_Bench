#!/usr/bin/env bash
set -euo pipefail
ACTOR_ROOT=/home/galbot/lizekai/RSI/api-ground-to-table/actor-adapter
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export TMPDIR="$ACTOR_ROOT/tmp" XDG_CACHE_HOME="$ACTOR_ROOT/cache"
export MPLCONFIGDIR="$ACTOR_ROOT/cache/matplotlib" TORCH_HOME="$ACTOR_ROOT/cache/torch"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
cd "$ACTOR_ROOT"
exec /home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -u actor.py "$@"
