# SIMPLE 复用与完整推理等待（2026-09-15）

用户最新纠正：已有 5090／ds4090 SIMPLE 管线，无需下载；Astra/xhigh 每个 chunk 的推理必须完整等待。本文是运行取证，不是策略可读的物体信息。

## 已读取的历史与本次核实

来源会话：`codex://threads/01a0a061-f80f-71b1-92a4-ca564af8b4f4`（标题“Claude会话关系与传输进度”）。其中 external-import-turn-139 附近记录原生 SIMPLE 水龙头策略闭环 4/5；更早记录 5090 的 `serve_exp8_openfaucet.py` 经端口 22086 反向隧道服务 ds4090 的 `pi05_decoupled_wbc`。这是旧 π0.5＋decoupled_wbc 结果，不能算作本任务 Astra＋ScaleBFM 的成功。

本次只读 SSH 连通成功：`ds4090` 的 hostname 为 `lidanshi-Z790M-AORUS-ELITE-AX`，用户目录 `/home/lidanshi`。已有 SIMPLE 为 `/home/lidanshi/lizekai/SIMPLE`，环境 `.venv/bin/python`。不要把本机的 `/home/galbot` 拼到远端路径。

已有组件：

- `src/simple/cli/eval_decoupled_wbc.py`：旧真实策略闭环评测入口。
- `src/simple/cli/replay_decoupled_wbc.py`：记录动作回放，`--sim-mode=mujoco_isaac` 是 MuJoCo 物理＋Isaac 同步渲染。
- `src/simple/cli/render_decoupled_wbc.py`：现成渲染入口；数据格式要读其实现，不重新造渲染栈。
- `scripts/render_sync_check.py`：已有相机／末端投影同步检查工具。
- `scalebfm/tracker.py`、`gate1_scene.py`、`gate1_c0_oracle.py`、`canon_replay_harness.py`：既有 model_38000 门任务与参考回放组件。

`gate0_stand.py` 的正式调用文档将模型目录指向 `/home/lidanshi/lizekai/scalebfm_runtime`，而非 SIMPLE/runtime。门 builder 引用现有 `data/robots/g1/g1_gate0_scene.xml` 与 `data/assets/articulated/003/output_mjcf/003.xml`。现有 tracker 的 `FUTURE_OFFSET_LAST=32.0`；当前 RSI ONNX 路线仍是已核实的25，不能因名称相同就直接替换封装。上述读取没有启动门场景物理。

后续只读实测：ds4090 的 SIMPLE/.venv 已有 mujoco、torch、onnxruntime、numpy、PIL。`scalebfm_runtime` 中原始 model_38000.pt 为66,812,193 bytes、model_38000_scripted.pt为16,258,772 bytes，metadata为3072 bytes；还保留eager scripted版本。无需重装基础依赖。实际原生环境代码为 `src/simple/envs/sonic_loco_manip.py`。这些检查没有进行模型推理或物理动作。

本轮不运行旧示教／oracle 来给 Direct 提供答案。完成十次当前抓取后，复用既有场景、命名关节接口、相机和视频管线；旧控制策略与本任务策略分别标注。Isaac 渲染不能写成 Isaac 物理评测。

本次进一步读取 `render_decoupled_wbc.py` 已确认：它从 LeRobot parquet 与 `meta/info.json`／`meta/episodes.jsonl` 读取关节名、base pose、object poses、environment_config；每帧设置记录状态、调用 `mj_forward`，再同步到 Isaac 渲染，**没有重新用动作产生物理轨迹**。这条入口适合忠实重渲染已记录轨迹，但其视频不能单独证明物理抓取成功。任务成功只取实际执行器／隐藏 evaluator 的原始回执；渲染所需 object poses 属于 actor 不可读的录像数据。

## 本次重复下载的记录

早先启动的 `simple-assets-0915` 下载在用户纠正后发出停止指令前已经结束，tmux 会话已退出。保存了 27,057,761 bytes 的公开资产包及 RSI 内的解压副本；没有改原环境，也没有删除任何文件。后续不再下载／安装 SIMPLE，直接复用既有远端。回执：`artifacts/R018/simple-data-preparation.json`。此前把本机某一 checkout 缺资产推断为整条 SIMPLE 管线不可用，是错误的范围外推。

## 推理与物理时钟

现有 `CodexPolicyAdapter.run_turn()` 按 app-server 的 `turn/completed` 事件结束，而不是按十秒估计。原事件等待仍有 900 秒上限，已用失败测试复现并改为 `next_message(None)`：完整等待消息；真实 EOF／连接错误仍上报；不因缓慢而重发 turn 或动作。协议初始化／启动请求保留独立通信超时，不把它当成策略推理期限。

修复后的六个 adapter 测试通过，包括单一 turn、无推理期限的回归测试。**R018 正在运行的进程加载的是修改前的代码；修复在下次安全启动时生效，不能冒称热更新已完成。**

当前 R018 属于同步诊断：仿真仅在动作服务中推进，Astra 推理时物理暂停。是否要求本轮同步改成“推理期间物理仍推进”已向用户明确提问；没有默默混为一谈。真机需要独立 tracker／PD 的持续运行，届时不得把等待 Astra 等同于停控制。

无论选择哪种时钟：tracker 的动作到位超时、策略思考等待、回合物理步数预算是三件不同的事。动作超时可带回新图像继续思考；不能自动截断模型，也不能把一次执行状态不明的动作重发。

### SIMPLE 动作与成功计数的源码核查

- 现有 `g1_sonic.py` 的 `decoupled_wbc` 分支接受 `target_q` 29维身体目标和左右各7维手指目标，以自己的 MOTOR_KP／MOTOR_KD 和 torque_limit 做PD。手指kp为5／2.5，并非当前RSI后端的20。接入时必须记录这个动力学差异，不把名字相同当成控制等价。
- `SonicLocoManipEnv.step` 在一帧中先调用 task.compute_reward，再调用 task.check_success；现有关门任务的check_success又调用compute_reward，每次满足关门条件给reward加0.03。因此不能把源码中的reward累加次数直接当成独立50Hz保持时间。
- 门旧条件是关节 `articulate_joint_1 < -0.16`，任务为关门。推开门需要独立、按物理时间而非重复reward调用计数的成功条件；旧策略和oracle不供Direct模仿。

### 门关节在录像中的保真问题

进一步检查本机同一管线的`render_decoupled_wbc.py`：重渲染帧只恢复observation.state中的robot joints、base_pose/base_vel以及自由物体object_poses，没有恢复articulate_joint_1等关节。`set_object_poses`也仅写自由关节，不涵盖门铰链。因此原LeRobot入口直接用于推门录像可能漏掉真实门运动；不能因此误判策略没有推门。

现有`MujocoSimulator.get_states()`已包含articulated_joints_state，`IsaacSimSimulator.step()`会按关节名恢复这些状态。下一阶段应保留逐帧完整关节状态及环境配置，按名称恢复到MuJoCo后再调用既有Isaac同步接口，不需要下载或重建渲染器。渲染状态属于host-only录像证据，禁止进入actor观察或经验提示。

`resolve_data_path(...,auto_download=True)`内部使用HF snapshot_download并在解压后删除归档。当前入口设置HF_HUB_OFFLINE防止网络下载；后续启动前必须沿用离线设置和已有RSI overlay，缺件就报告具体路径，不能触发该自动下载／删除流程。

### 推门入口仍须验证的推侧与方法语义（尚未运行）

静态资产几何及既有gate1说明表明，门根姿态为identity时正铰链方向向+X开启。原SIMPLE CloseDoor把门根绕Z旋转约π，并把机器人放在其-X侧；因此只将铰链设到下限可能把机器人放在开门的拉侧。当前rsi/simple_environment.py是未验证草稿，首次推门前必须检查真实场景与开门方向，必要时在隔离任务变体中调整门朝向或机器人初始侧，并记录完整配置；不能把拉门结果误称推门。

DoorPushEvaluator目前只验证手接触、角度增加和物理保持时间，还不能单凭这三项证明动作方式是推而非拉。推侧布置及动作/视频审计仍是进入推门计数前的必要验证项。原关门任务与新推开门变体分别统计，不能混用旧奖励。
