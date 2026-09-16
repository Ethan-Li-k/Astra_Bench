# 当前 UMI-4 机器人合同

本体是自由站立 G1 + 双 DEX3，底层为原始 `model_38000.onnx`。ScaleBFM 模式固定
为 UMI-4，跟踪 `left_wrist_yaw_link`、`right_wrist_yaw_link`、
`left_ankle_roll_link`、`right_ankle_roll_link`。跨模块只按名称映射。

`observe()` 返回观测编号、具名 q29、指关节、四点实测世界 pose、当前 reference、
位置误差和上一命令状态。四元数为 wxyz。host 另存仿真 track、头部和右腕 RGB；
track 不是现有真机传感器。观测不包含
方块 pose、接触、奖励或成功真值。

`move_four_points(observation_id, command_id, targets, duration,
position_names, orientation_names)` 接收四个完整绝对 pose，并显式声明本步激活的
位置／姿态 link。每个激活分量相对该观测最多 3 cm、0.1 rad；duration 为
0.5–3.0 s。host 从当前 reference 出发，只覆盖激活分量，然后生成 34 帧
minimum-jerk/SO(3) 参考。`target_reached` 要求激活位置误差低于 1 cm、激活姿态
误差低于 0.05 rad，连续五个 50 Hz tick；回执仍报告全部四点残差。

`translate_target()` 和 `rotate_target()` 只从最新观测编译具名目标。旋转向量方向
是世界轴，模长是弧度；pivot 也是世界坐标。它们不执行、不解 IK，也不证明可达。

`set_grippers(left, right)` 使用闭合比例，0 张开、1 到 DEX3 closed profile。这是
机械命令，不是指间距、力、接触或抓住证据。`move_wrist()` 与 `set_gripper()` 仅为
旧右腕诊断兼容入口，不是新策略合同。

ScaleBFM 每 20 ms 更新，PD 每 4 ms 更新。当前 harness 是进程内阻塞式仿真原型；
动态 tool schema 与单回合 dispatcher 已存在，但独立 app-server、实时线程和真机
两阶段 stale-plan 复核尚未实现。不能把暂停仿真或延长 0.5 s 观测期限当作真机方案。

Jᵀ 手部位置补偿目前只有显式仿真候选开关，GPT 不得调整其力矩或增益。它改善
了 HOLD 与平移的位置误差，但没有通过旋转或真机认证。6D WristPI 在其他
Loco_manip tracker 上有 sim/真机同源实现，本任务的 model_38000 right-yaw 对照仍
超时。π0.5 数据生成、评测和部署必须记录并保持相同 control profile。

`right_palm` 相对 `right_wrist_yaw_link` 的资产 FK 为 `[0.08,0,0] m`，但它不是
经接触标定的 TCP。不得复用 Panda/X5 偏移。
