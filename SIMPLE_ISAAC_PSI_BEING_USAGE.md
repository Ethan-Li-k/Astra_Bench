# psi_being 上的 SIMPLE/Isaac：本地 Codex 操作说明

更新日期：2026-09-17

## 1. 先明确本机与远端的关系

- **本机**是 `galbot-System-Product-Name`，GPU 为 RTX 5090 D v2。本机负责 RSI 的计划、skill/runtime 发布、训练状态与验收；当前权威约定是 `/home/galbot/lizekai/RSI/CURRENT_EFFECTIVE_CONTRACT.md`。
- **远端**是 SSH 别名 `psi_being`，实际地址为 `root@10.0.6.131:22`，远端主机名是 `kaic-b2e086c2-8f30-4e8a-9b60-c87c25e0f9ec-0`，有 2 张 RTX 4090。远端承载本次新建的 SIMPLE 0.1.0、Isaac Sim 4.5、MuJoCo 3.3.6 与 CuRobo 环境。
- 两台机器的文件系统**互不共享**。两边都出现 `/home/galbot/...` 只是路径同名，不能据此认为文件同步。本机路径不能直接传给远端程序，反之亦然。
- 本机通过 `ssh psi_being` 执行远端命令；文件必须显式用 `scp` 或 `rsync` 传输，并在关键配置、数据和权重交接时记录大小、文件数或 sha256。
- SSH 登录用户虽然是 `root`，本环境的激活脚本会把 `HOME`、XDG 与 uv 缓存切到 `/home/galbot/lizekai/RSI/simple-isaac-20260917/`，避免写入 `/root`。

SSH 配置已存在于本机 `~/.ssh/config`：

```sshconfig
Host psi_being
    HostName 10.0.6.131
    User root
    Port 22
    IdentityFile ~/.ssh/psi_being
    IdentitiesOnly yes
```

## 2. 环境位置与进入方式

远端唯一入口：

```bash
ssh psi_being
source /home/galbot/lizekai/RSI/simple-isaac-20260917/activate.sh
```

激活后工作目录自动切到：

```text
/home/galbot/lizekai/RSI/simple-isaac-20260917/SIMPLE
```

关键位置：

```text
环境根目录  /home/galbot/lizekai/RSI/simple-isaac-20260917
代码仓库    /home/galbot/lizekai/RSI/simple-isaac-20260917/SIMPLE
Python环境  /home/galbot/lizekai/RSI/simple-isaac-20260917/SIMPLE/.venv
激活脚本    /home/galbot/lizekai/RSI/simple-isaac-20260917/activate.sh
日志目录    /home/galbot/lizekai/RSI/simple-isaac-20260917/logs
安装回执    /home/galbot/lizekai/RSI/simple-isaac-20260917/INSTALL_RECEIPT.md
```

激活脚本固定了 `MUJOCO_GL=egl`、`OMNI_KIT_ACCEPT_EULA=Y`、`TORCH_CUDA_ARCH_LIST=8.9+PTX`，并隔离 Python、HOME 和缓存。用户已明确接受 NVIDIA Omniverse EULA；不要移除或把该接受扩展到其他未授权环境。

快速只读检查：

```bash
python -c 'import simple, mujoco, torch; print(mujoco.__version__, torch.__version__, torch.cuda.get_device_name(0))'
python scripts/list_env.py
```

Isaac 最小验收：

```bash
python /home/galbot/lizekai/RSI/simple-isaac-20260917/isaac_headless_smoke.py
```

基准验收日志是 `logs/isaac-headless-acceptance.log`，应包含：

```text
ISAAC_SIMULATION_APP=STARTED
ISAAC_UPDATE=OK
ISAAC_PROCESS_EXIT=0
```

无显示器时出现 GLFW/windowing 与音频 null-streamer warning 是已知的无头提示；判失败要看 `[Error]`、traceback、非零退出码或缺失上述 marker。

## 3. “SIMPLE 训练”在这里具体指什么

SIMPLE 仓库提供仿真环境、数据生成与策略评测客户端。它不在这个仓库里训练 Psi-0 模型权重：

- `datagen` 为支持的 motion-planning 任务生成 LeRobot 数据。
- Psi-0 的 checkpoint 训练/后训练在独立的 Psi-0 仓库完成。
- `uv run eval` 和 `uv run eval-decoupled-wbc` 连接策略推理服务，在 SIMPLE 中做闭环 rollout。
- 当前 RSI 的“训练”是 GPT-as-Policy 的 skill/rollout 学习，由本机现有 RSI dispatcher、runtime 和发布体系管理；不能用一次 `datagen` 或渲染替代训练回合，也不能把渲染结果写成物理测试结果。

新远端环境已经能运行官方 SIMPLE/Isaac 客户端，但**尚未自动接入本机当前 RSI campaign**。当前 `isaac-readiness.json` 仍将官方同 setting 适配标为 pending：原生 MP ActionCmd、Teleop WBC、保存的 reset、在线 Isaac `head_stereo_left` 以及原生终止语义还需在同一适配器内闭环验证。因此，本地 Codex 不得仅因环境安装成功就宣称六项 Isaac 测试已开始或训练已迁移完成。

## 4. 当前 RSI 任务边界

每次调度前先读：

```bash
cat /home/galbot/lizekai/RSI/CURRENT_EFFECTIVE_CONTRACT.md
python3 -m json.tool /home/galbot/lizekai/RSI/artifacts/six-transfer-20260917/plan.json
python3 -m json.tool /home/galbot/lizekai/RSI/artifacts/six-transfer-20260917/execution/status.json
cat /home/galbot/lizekai/RSI/skills/releases/CURRENT.json
```

当前选择的四个训练环境是：

```text
simple/G1WholebodyTabletopGraspVariant1MP-v0
simple/G1WholebodyBendPickSimToRealTeleop-v0
simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0
simple/G1WholebodyMobilePickAndPlaceCheezitTeleop-v0
```

先 2 路校准，只有实测显存、吞吐、reset 隔离和日志隔离后才能升到最多 4 路；两张 GPU 不等于已经验证 4 路或 8 路并行。四项训练各至少 5 次完整独立尝试。历史成功只作为经验，不重训复试。

以下六项是冻结测试集，各 5 次，与训练账分开，测试中不能学习或修改判据：

```text
simple/G1WholebodyXMovePickTeleop-v0
simple/G1WholebodyBendPickMP-v0
simple/G1WholebodyHandoverTeleop-v0
simple/G1WholebodyLocomotionPickBetweenTablesTeleop-v0
simple/G1WholebodyTabletopGraspMP-v0
simple/G1WholebodyXMoveBendPickTeleop-v0
```

本轮官方后端固定为 `mujoco_isaac`：MuJoCo 执行物理，Isaac 同步提供在线 actor RGB。`sim_mode=isaac` 的 PhysX 路线不属于本轮；离线重渲染也不算在线 Isaac 评测。六项测试当前仍是 `new_test_results: 0`，不能提前记成功或完成。

## 5. 官方 SIMPLE 命令的安全起步方式

先用一个 episode 验证任务、资产、相机和输出目录，再扩大。所有输出留在 RSI 环境根目录下，避免写 `/root` 或改动既有 `psi_deploy`、`.venv-psi`。

Motion-planning 数据生成示例（这只是官方数据生成，不计作 RSI skill 训练）：

```bash
source /home/galbot/lizekai/RSI/simple-isaac-20260917/activate.sh
CUDA_VISIBLE_DEVICES=0 uv run datagen \
  simple/FrankaTabletopGraspMP-v0 \
  --sim-mode mujoco_isaac \
  --headless \
  --no-webrtc \
  --num-episodes 1 \
  --save-dir /home/galbot/lizekai/RSI/simple-isaac-20260917/runs/datagen-smoke
```

MP 任务的官方策略评测使用 `uv run eval`。不要直接输入 `eval`，因为 Bash 内建命令同名：

```bash
CUDA_VISIBLE_DEVICES=0 uv run eval \
  simple/G1WholebodyBendPickMP-v0 \
  psi0 train \
  --data-format lerobot \
  --data-dir /absolute/remote/path/to/simple-eval/G1WholebodyBendPickMP-v0/level-0 \
  --host 127.0.0.1 \
  --port 21000 \
  --sim-mode mujoco_isaac \
  --headless \
  --num-episodes 1 \
  --episode-start 0 \
  --eval-dir /home/galbot/lizekai/RSI/simple-isaac-20260917/runs/eval-mp-smoke
```

Teleop 后缀任务使用 decoupled WBC 入口：

```bash
CUDA_VISIBLE_DEVICES=1 uv run eval-decoupled-wbc \
  simple/G1WholebodyXMovePickTeleop-v0 \
  psi0_decoupled_wbc train \
  --data-format lerobot \
  --data-dir /absolute/remote/path/to/simple-eval/G1WholebodyXMovePickTeleop-v0/level-0 \
  --host 127.0.0.1 \
  --port 21000 \
  --sim-mode mujoco_isaac \
  --headless \
  --num-episodes 1 \
  --episode-start 0 \
  --eval-dir /home/galbot/lizekai/RSI/simple-isaac-20260917/runs/eval-wbc-smoke
```

这些评测命令只有在远端存在对应的官方 eval dataset、原生控制依赖和可访问的策略服务时才执行。训练转换后的 LeRobot 数据如果缺少 `environment_config`，不能代替官方 eval dataset。

## 6. 策略服务与网络

`--host 127.0.0.1` 在远端命令里指 **psi_being 自己**，不指本机。

如果策略服务也运行在 psi_being，直接用远端 `127.0.0.1:<port>`。如果策略服务运行在本机，需要从本机建立 SSH 反向端口转发：

```bash
# 在本机执行；本机策略服务监听 127.0.0.1:21000
ssh -N -R 21000:127.0.0.1:21000 psi_being
```

保持该连接后，远端 SIMPLE 客户端才能用 `--host 127.0.0.1 --port 21000` 访问本机服务。启动 rollout 前先在远端验证端口；未知连接状态不能重放已经发出的策略请求或动作。

## 7. 长任务必须用 tmux + tee

在远端交互 shell 中创建会话，再把命令发送进去：

```bash
tmux new-session -d -s simple-datagen-0917
tmux send-keys -t simple-datagen-0917 \
  'source /home/galbot/lizekai/RSI/simple-isaac-20260917/activate.sh; export CUDA_VISIBLE_DEVICES=0; uv run datagen simple/FrankaTabletopGraspMP-v0 --sim-mode mujoco_isaac --headless --no-webrtc --num-episodes 1 --save-dir /home/galbot/lizekai/RSI/simple-isaac-20260917/runs/datagen-smoke 2>&1 | tee -a /home/galbot/lizekai/RSI/simple-isaac-20260917/logs/datagen-smoke.log' Enter
```

查看而不 attach：

```bash
tmux ls
tail -n 100 /home/galbot/lizekai/RSI/simple-isaac-20260917/logs/datagen-smoke.log
```

人工接管才用 `tmux attach -t simple-datagen-0917`，完成并确认日志后再杀 session。每个并行 lane 必须有独立 session、GPU、输出目录、reset 和日志。

## 8. 文件传输与结果回收

从本机送一个普通配置到远端：

```bash
rsync -av --checksum /home/galbot/lizekai/RSI/<local-file> \
  psi_being:/home/galbot/lizekai/RSI/simple-isaac-20260917/incoming/
```

从远端拉回日志或小型报告：

```bash
rsync -av --checksum \
  psi_being:/home/galbot/lizekai/RSI/simple-isaac-20260917/logs/ \
  /home/galbot/lizekai/RSI/artifacts/psi-being-simple-logs/
```

权重、dataset、episode cache、视频和评测产物不能随意删除。清理前必须确认长期第二份副本真实存在且完整，记录文件数、总字节数，关键件校验 sha256。临时远端不算长期第二份副本。

## 9. 当前交付状态与接入门槛

已完成：官方版本环境安装、CuRobo 4090 编译、MuJoCo EGL、31 个环境注册、Isaac 4.5 无头启动/update/退出验收。

接入当前 RSI campaign 前仍需完成：

1. 把本机适配器代码与必要数据显式同步到远端独立目录，不覆盖既有环境或资产。
2. 分别验证 MP 的原生 ActionCmd 与 Teleop 的原生 WBC；跨模块关节量按名字映射。
3. 用同一个保存 reset 验证 MuJoCo 状态、在线 Isaac `head_stereo_left`、动作 ACK、原生 reward/terminal 的因果一致性。
4. 单 lane 完整闭环后测 2 lane；记录显存、吞吐和输出隔离，再决定是否升到 4 lane。
5. 训练完成后冻结 skill/harness、控制 checkpoint、机器人/手型、资产、相机、动作接口、episode record 与判据，才可开始六项各 5 次预评测。

官方资料：

- 安装说明：https://psi-lab.ai/SIMPLE/docs/tutorials/installation.html
- SIMPLE 仓库：https://github.com/physical-superintelligence-lab/SIMPLE
- 本次固定仓库 commit：`6d10628794d9c7de4596b4f2afb2c054a637c2bc`
