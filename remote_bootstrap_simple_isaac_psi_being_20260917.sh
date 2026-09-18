#!/usr/bin/env bash
# Bootstrap the official SIMPLE native uv environment on psi_being.
# All mutable state is kept under the RSI project root on that host.
set -Eeuo pipefail

BASE=/home/galbot/lizekai/RSI/simple-isaac-20260917
REPO="$BASE/SIMPLE"
BIN_DIR="$BASE/bin"

install -d -m 755 "$BASE/logs" "$BIN_DIR" "$BASE/cache/uv" "$BASE/python"
export PATH="$BIN_DIR:/usr/local/cuda/bin:/usr/bin:/bin"
export UV_CACHE_DIR="$BASE/cache/uv"
export UV_PYTHON_INSTALL_DIR="$BASE/python"
export UV_HTTP_TIMEOUT=3000
export GIT_LFS_SKIP_SMUDGE=1
export GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf
export GIT_CONFIG_VALUE_0=git@github.com:
export CUDA_HOME=/usr/local/cuda
export TORCH_CUDA_ARCH_LIST=8.9+PTX
export MUJOCO_GL=egl

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$BIN_DIR" UV_NO_MODIFY_PATH=1 sh
fi
uv --version

if [[ ! -d "$REPO/.git" ]]; then
  git clone https://github.com/physical-superintelligence-lab/SIMPLE.git "$REPO"
fi

cd "$REPO"
git lfs install --local
git config --local url.https://github.com/.insteadOf git@github.com:
git submodule update --init --recursive
git lfs pull

git rev-parse HEAD | tee "$BASE/SIMPLE_COMMIT.txt"
git status --short --branch

uv sync --all-groups --index-strategy unsafe-best-match
bash scripts/install_curobo.sh

uv run python -c 'import simple; print("SIMPLE_VERSION=" + str(simple.__version__))'
uv run python scripts/list_env.py
