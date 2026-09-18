# SIMPLE Isaac environment receipt — psi_being — 2026-09-17

## Scope and location

- Host: `psi_being` (`10.0.6.131`)
- Environment root: `/home/galbot/lizekai/RSI/simple-isaac-20260917`
- SIMPLE checkout: `/home/galbot/lizekai/RSI/simple-isaac-20260917/SIMPLE`
- SIMPLE commit: `6d10628794d9c7de4596b4f2afb2c054a637c2bc`
- Activation script: `/home/galbot/lizekai/RSI/simple-isaac-20260917/activate.sh`

## Host evidence

- Ubuntu 22.04.4 LTS
- 2 × NVIDIA GeForce RTX 4090, compute capability 8.9
- NVIDIA driver 550.54.14
- CUDA toolkit 12.4

## Installed environment

- Python 3.10.12
- SIMPLE 0.1.0
- Isaac Sim 4.5.0.0
- MuJoCo 3.3.6
- PyTorch 2.7.0+cu128
- CuRobo built with `TORCH_CUDA_ARCH_LIST=8.9+PTX`
- `warp-lang` pinned to 1.7.0 by the repository installer

## Verified

- `torch.cuda.is_available()` is true and GPU 0 resolves to RTX 4090.
- All five CuRobo CUDA extension modules load successfully.
- `scripts/list_env.py` lists 31 registered SIMPLE environments.
- MuJoCo EGL import works after installing `libegl1` and `libgles2`.
- The user explicitly accepted the NVIDIA Omniverse EULA; the isolated activation script sets `OMNI_KIT_ACCEPT_EULA=Y`.
- Isaac Sim 4.5 starts headlessly on RTX 4090, reaches `app ready`, completes one `SimulationApp.update()`, shuts down, and returns process exit code 0.
- The acceptance log contains `ISAAC_SIMULATION_APP=STARTED`, `ISAAC_UPDATE=OK`, and `ISAAC_PROCESS_EXIT=0`, with no `[Error]` or traceback.

## Runtime notes

- Added runtime libraries `libegl1`, `libgles2`, `libice6`, `libsm6`, and `libxt6`. The X11 libraries resolve the prior `libhdx.so` dependency cascade.
- Installed system `ripgrep`; it remains available after activating the isolated environment, so local Codex can use the required `rg` workflow without inheriting Conda.
- Headless GLFW/windowing and null-audio warnings are expected on this host and did not prevent startup, update, shutdown, or a zero exit code.
- Environment installation is complete. Wiring this environment into the current RSI campaign's native MP/WBC adapter and frozen six-task evaluation remains a separate integration step; installation success is not an evaluation result.

## Evidence logs

- `logs/apt-prereqs.log`
- `logs/bootstrap.log`
- `logs/egl-runtime-install.log`
- `logs/x11-runtime-install.log`
- `logs/non-eula-verification.log`
- `logs/isaac-headless-acceptance.log`

## Operator documentation

- Local authoritative copy: `/home/galbot/lizekai/RSI/SIMPLE_ISAAC_PSI_BEING_USAGE.md`
- Remote copy: `/home/galbot/lizekai/RSI/simple-isaac-20260917/LOCAL_CODEX_USAGE.md`
