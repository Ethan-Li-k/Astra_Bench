# RSI 四点视觉操作开发

当前主线是 `model_38000.onnx` 的 ScaleBFM UMI-4：GPT 或任务训练后的 π0.5
输出双腕、双踝四点世界位姿，统一 harness 将其编译为 50 Hz 参考并由 250 Hz
PD 执行。项目 skill 见
[loco-manip-four-point-policy](.cursor/skills/loco-manip-four-point-policy/SKILL.md)。

当前只支持 MuJoCo 仿真。没有调用额外模型 API，没有通过能力审计的 humanoid π0.5
checkpoint，也没有真机认证。SIMPLE 已有静态具名动作 bridge，但动态 backend 因本地
缺少 articulated asset 003 而未连接。最新失败与下一步见 [ITERATIONS.md](ITERATIONS.md)。

R017 已完成首个真实 Astra/xhigh 无示教 Direct 回合：4 个动作、3 次连续跟踪超时，
native 任务未完成。[视频和复盘](ref/R017_DIRECT_PILOT_REVIEW.md)记录了初始手桌
接触、无模型精确回放，以及被完整 reset 检查否定的桌沿位移候选。
[RTC、history、memory 与 π0.5 设计](ref/DIRECT_RTC_MEMORY_DESIGN_20260915.md)
区分上游事实、现有功能和待验证方案。新增环境与存储规则见 [AGENTS.md](AGENTS.md)。

## 代码入口

- `rsi/four_point.py`：具名 UMI-4 pose、世界平移／旋转和 minimum-jerk/SO(3) 插值。
- `rsi/scalebfm.py`：model_38000 专用 UMI-4 adapter，关节和 body 都按名称映射。
- `rsi/live.py`：桌面红块 MuJoCo backend、active-aware WristPI、四点执行、DEX3 与回执。
- `rsi/policy_harness.py`：direct/hybrid schema、RGB 像素投影、局部 EEF 编译、回合记录和 π0.5 gate。
- `rsi/evaluator.py`：宿主侧原生任务验收；actor 只收到三态 outcome。
- `rsi/task_skill.py`：DRAFT/CANDIDATE/FROZEN task-skill 生命周期判定。
- `rsi/tool_host.py`：GPT-as-Policy 式单回合动态工具 dispatcher 与审计。
- `rsi/codex_app_server.py`：持久 Codex thread/turn 与动态工具路由。
- `rsi/stdio_transport.py`：Codex app-server JSON-RPC stdio transport。
- `rsi/simple_bridge.py`：按关节名把 q29 与双 DEX3 目标编译为 SIMPLE action。
- `tools/four_point_rollout.py`：无 GPT 的 HOLD／平移／旋转 smoke 与 RGB 截图。
- `tools/codex_direct_sim.py`：5 秒 settling 后显式启动 Astra Direct；运行才使用套餐额度。
- `tools/hand_force_probe.py`：无局部控制、Jᵀ 位置补偿和 6D WristPI 的固定对照。
- `tools/wrist_pi_direction_probe.py`：active-aware WristPI 的固定方向重复测试。
- `tools/gripper_probe.py`：左右 DEX3 动态张开／闭合／张开验收。
- `tools/oracle_grasp_probe.py`：特权开发机械探针，明确禁止进入训练或 ICL。
- `tools/simple_scalebfm_audit.py`：SIMPLE 离线依赖与 model_38000 接口审计，不是 rollout。
- `tools/vision_reach_probe.py`：无 GPT 的 RGB-plane-EEF 短程闭环诊断，不读取物体状态。

测试使用已有隔离环境，不安装依赖：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src \
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python \
  -m unittest discover -s tests -v
```

一次新 smoke（输出目录不可复用）：

```bash
MUJOCO_GL=egl PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src \
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python \
  tools/four_point_rollout.py --output artifacts/RXXX/new-hold --primitive hold
```

可选 primitive 为 `hold`、`right-x` 和 `right-yaw`。它们是接口与 tracker 诊断，
不评估抓取。超过 60 秒的仿真必须按项目 AGENTS.md 用 tmux 和 tee。

## 当前入场条件

红块 seed task 的顺序是 HOLD、腕部平移、腕部旋转、双 DEX3、视觉接近、闭合、
抬升与视觉复核。原始 ONNX HOLD 双腕误差为厘米级。当前 execution profile 使用
active-aware 6D WristPI；右腕 +20 mm world-X 与 +0.08 rad world-Z 各三次确定性测试
通过，而 -0.08 rad world-Y 在 0.0535 rad 姿态误差处失败，因此一般姿态 gate 尚未
通过。旧 Jᵀ 只保留为历史诊断，不进入真机候选。双 DEX3 free-space 开闭已通过，
纯夹爪 waypoint 会平滑闭合，但该回执不证明接触。头相机可见红块，右腕相机严重
自遮挡。最新特权机械 oracle 完成四个小 pregrasp chunk，第五个超时且仍未接触方块；
其数据禁止进入 ICL、训练和评测。当前还需标定抓取点/TCP、方块宽度闭合量并完成
视觉闭环接触与抬升，才能启动有意义的自主 seed 评测。

R015 已把 head RGB 同帧相机标定、`image_pixel_to_world_plane` 和
`four_point_place_local_point` 串通；真实 episode 可仅从红块可见像素与显式工作台平面
编译 EEF 远目标。默认场景中 vector 与 largest-axis 两种视觉 reach 都在第二段超时，
右腕停在约 world-X 0.12 m。四点整体 +20 mm 时双腕到位、双踝误差仍约20 mm，说明
静态脚点平移不是步态。把桌子向机器人移动14 cm 虽能稳定站立，却使腕部 X/Z 动作受限；
视觉闭手—抬升保持 `in_progress`。该 offset 已拒绝作为 seed。下一步应从可达初始全身
构型或一条成功示范形成抓取 task adapter，而不是继续扫腕步长、夹爪闭合量或桌子位置。

Direct 动态工具为 `loco_start`、`four_point_translate`、
`four_point_rotate`、`image_pixel_to_world_plane`、
`four_point_place_local_point`、`scalebfm_act`。Hybrid 将最后一项替换为
`pi05_infer` 与 `loco_execute`：π0.5 只生成 proposal，GPT 必须向
`loco_execute` 提交审阅后的完整 response，host 才会经同一 validator 下发。
Hybrid 启动会先核验 π0.5 capability manifest：必须是视觉输入、任务训练的人形
checkpoint，输出匹配 UMI-4 SE(3)+双夹爪合同，并固定 checkpoint/normalizer hash。
现有 M3 server 把图像设为 `None`，因此被明确拒绝用于视觉抓取。SIMPLE 的 q29/DEX3
具名映射已通过静态接口检查，动态 reset 被缺失的 articulated asset 003 阻塞，没有
自动下载或冒充 backend 成功。Codex app-server 0.154 的 `initialize` 握手已通过，
但尚未创建 thread/turn，因此本项目模型调用仍为0。
