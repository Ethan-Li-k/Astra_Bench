# SIMPLE 门任务：GPT-6 / π0.5 / ScaleBFM 方案

状态：架构审计与实现指令，2026-09-15。没有调用 GPT API，没有启动真机，也没有声称已完成开门。

## 结论先行

旧 SIMPLE 任务实际是 `G1WholebodyCloseDoorTeleop-v0`，目标是**关门**。它不是视觉策略：生成器读取门位姿、铰链、门角、接触和 role 等特权信息，再用固定 whole-body 参考驱动 ScaleBFM。

新任务若按用户所写改成**开门**，不能沿用旧的运动方向和成功阈值。建议保留旧资产与隐藏 evaluator，重建 actor 可见观测和动作层：

```text
Direct: RGB + 本体 + 同回合历史 -> GPT-6 -> 有界任务空间动作 -> harness -> ScaleBFM + DEX3

π0.5-only baseline:
RGB + 本体 + 指令 -> humanoid π0.5 proposal -> harness -> ScaleBFM + DEX3

Hybrid:
RGB + 本体 + 指令 -> humanoid π0.5 proposal
                    -> GPT-6 outcome/intent gate
                    -> student / edit / eef
                    -> harness -> ScaleBFM + DEX3
```

先在红块抓取／抬升 seed task 上形成并冻结 UMI-4 skill。Direct 用于检验 harness、视觉反馈和 ScaleBFM；π0.5 经过 G1 四点动作空间微调后才能进入第二、第三条链。门任务是同一 skill 的后续任务适配，不另造底层合同。

## 两个旧线程给出的原始事实

### 旧任务内容

- SIMPLE 注册任务：`simple/G1WholebodyCloseDoorTeleop-v0`。
- 物理步长 5 ms，原环境控制 200 Hz，reward/任务判定 20 ms；接入 ScaleBFM 后 tracker 按 50 Hz 更新，PD 在物理步运行。
- 门铰链 `articulate_joint_1` 的范围是 `[-0.17453, 1.39626] rad`；`q > 0` 表示打开，关门令 q 减小。
- 旧成功条件：门角 `q <= -0.16 rad` 连续至少 17 个 50 Hz tick（0.34 s）；另记录跌倒与关节限位。
- 最终窄门角生产域为 `U(0.35, 0.50)`；更大门角只作 OOD 诊断。

### 旧数据格

- C0：双手空闲，指定右手关门。
- C1：双手持物，指定右侧骨盆关门。
- Cneg：双手持物，保持不动，门不应产生进展。
- 另有不点名执行器的 IMPLICIT 诊断集，用于检查是否能从视觉和 occupancy 选择动作部位。

这些数据格的目的主要是训练/评估执行器切换，不是证明一个只看 RGB 的 agent 能发现门、定位把手并规划开门。

### C0 最终执行机制

旧 C0 不是七段状态机的完整闭环实现。最终生产切换到已认证的固定 oracle：

1. 机器人在固定相对位置和约 `0±5°` yaw 初始化。
2. 两肘参考约 1.2 rad，肩 pitch 约 0.2 rad，形成前收臂姿态。
3. whole-body 世界参考沿 X 推进 0.6 m，5 s minimum-jerk，再保持 5 s。
4. 右手/手指/腕与门板中部碰撞，推动门角进入关闭区。

最终生产记录为 C0 36/36 出现门事件、33/36 达到 positive；3 条因超出参考关节限位包络被拒。这个结果证明固定初态下的推门 mechanic 可驱动 ScaleBFM，不证明视觉泛化或把手操作。

### runtime 线程的有效结论

- model_38000 接收 14-body 容器中的 UMI-4 有效参考，输出 29 维动作，再解码为 `q_target` 并由 PD 执行；有效点为双腕与双踝。
- 29 关节必须按名称映射；模型顺序为左腿 6、右腿 6、腰 3、左臂 7、右臂 7。
- proprio/action history 必须是真滚动历史；旧的“当前帧重复三次”已经被定位为 D1 故障。
- 旧 SIMPLE 快照先后出现远期 index 33、32。当前 RSI ONNX 路线已核实使用 `(0,1,2,3,4,25)`，不能因为旧门任务通过就改回旧值。
- 旧 runtime certificate 是 free-space / 有限门 mechanic 证据，不能替代当前 DEX3、视觉、精细 TCP 和长期运动质量验收。

## GPT-as-Policy 中真正要复用的东西

这个仓库没有一个可以直接导入并接管 ScaleBFM 的通用 `policy` 类。可复用的是以下 harness 结构：

1. 同一回合持续存在的 agent 上下文。
2. 原始任务指令、机器人合同、同回合 NOTES 分层提供。
3. 每次动作绑定最新 `observation_id` 和唯一 `request_id`。
4. host 校验单位、坐标系、有限值、动作幅度、顺序和新输出目录。
5. 短动作后必须重新观察；ACK 不等于到位，夹爪闭合不等于抓住。
6. Hybrid 分开判断上一段执行结果和下一段 student 意图；只有看到失败或意图错位才 edit/eef 接管。
7. student proposal 的机器人 FK 只用于可达性和意图检查，不预测门、接触或成功。

对 G1 的关键修改是：GPT 思考期间仿真/真机不能停。ScaleBFM 50 Hz 与 PD 250 Hz 必须运行在独立实时线程，保持最后批准的 reference。

## 统一执行 harness

Direct、π0.5-only 和 Hybrid 必须共用同一个执行层，避免每条路线的安全边界和成功条件不同。

### Actor 可见观测

- 头部 RGB；有腕相机后再加入左右腕 RGB。
- 具名 q29/dq29、pelvis 状态、左右腕实测 pose、当前 reference、reference tracking error。
- DEX3 最近一次开合命令；在没有传感器标定前不能称为实测指间距或抓力。
- 上一个命令的接受、执行、到位、超时、取消和当前误差。
- 同回合前后图像与公开 NOTES。

禁止给 GPT/π0.5：门 qpos、门 link 世界 pose、铰链轴、接触 geom、奖励、成功位、物体真值。上述字段可留在隐藏 evaluator 和开发日志中。

### 首版动作合同

策略只提交短任务空间动作，不提交 action29、q29 或力矩：

动作 schema 的完整示例见项目 skill 的 `CONTROL_CONTRACT.md`。策略每个 waypoint 显式
给出双腕、双踝绝对世界 pose 与左右 DEX3 closure；每点位置不超过 3 cm、旋转不超过
0.1 rad、每 chunk 1–5 个 waypoint。

harness 将动作变成 50 Hz minimum-jerk/SO(3) 的 34 帧 UMI-4 reference；ScaleBFM
在 14-body 容器中只激活双腕双踝。DEX3 由独立手控制器同步执行，不能塞进 29 维 body action。

运行时未激活 body 的 reference 使用当前实测/稳定 reference 构造，并由 mode mask 标为 inactive。训练数据中没有标签的 body 则必须 `valid_mask=0`，不能用零或假中性标签参与 loss。这两个场景不能混为一条规则。

### 陈旧观测

当前 `move_wrist` 的 0.5 s 有效期无法覆盖 GPT-6 推理。新服务采用两阶段提交：

1. policy 基于 `observation_id` 产生固定任务空间目标。
2. 执行前取最新机器人状态，只做漂移与命令版本检查。
3. 漂移超过阈值则返回 `STALE_PLAN` 并要求重新观察；不静默把目标重新锚到最新手腕。
4. 接受后实时线程持续执行，模型请求线程不持有物理锁。

## Direct GPT-6 开门

GPT-6 通过 Responses API 接收图像与文本观测，并用 Structured Outputs / function calling 产生上面的动作对象。模型不直接访问控制进程，也不输出自由格式关节命令。

建议的视觉状态机：

1. `OBSERVE_DOOR`：确认门板、可推动区域和机器人手的位置。
2. `PRE_CONTACT`：用小幅腕部位置/姿态动作接近门板或把手区域。
3. `CONTACT_OR_GRASP`：若资产只有门板，采用推开；若未来资产有可动把手，才启用 DEX3 闭合和把手旋转。
4. `SWING`：依据连续图像中的门边缘运动分段跟随，不用隐藏铰链坐标生成整条弧。
5. `VERIFY`：由图像确认门开度持续增加；必要时撤回“已接触/已抓住”的旧判断。
6. `RETRACT`：停止施力并回到稳定姿态。

当前 003 资产审计只证明有门板碰撞与铰链，没有找到可动 handle/latch 合同。因此第一版应命名为 `push_open_door_panel`。`grasp_handle_and_pull_open` 是后续资产能力，不能用 prompt 伪造。

## π0.5 与 ScaleBFM

原 GPT-as-Policy RoboDojo π0.5 输出 X5 的 `[左臂6, 左夹爪, 右臂6, 右夹爪]`。它与 G1/ScaleBFM 不兼容。

本地可复用的数据合同是 UMI-4 task space：

- 左右腕与左右踝的 pose；
- 派生 pelvis SE(2)；
- hand/gripper 字段；
- 旋转必须从 source codec 解码到 SO(3)，做 SE(3) 重锚，再编码为 ScaleBFM codec；
- body 按名称映射；公开四点序为腕、腕、踝、踝，模型 14-body active index 为踝、踝、腕、腕，禁止位置拷贝。

π0.5 需要在这个 action contract 上进行 G1 专用微调，输出未来 task-space chunk。推理 adapter 再把有效 body target 和 mask 编译成 34 帧参考，ScaleBFM 从中采样六个 future offset。没有这个微调 checkpoint 时，π0.5 路线只能做接口 smoke/HOLD，不能进入开门评测。

Hybrid 每轮流程为：

1. 从最新观测生成一个新的 π0.5 proposal。
2. 展开 robot-only FK，检查 proposal 大致朝向、腕姿、夹爪阶段和局部可达性。
3. GPT-6 分别审查上一段真实结果和下一段 proposal 意图。
4. 选择 `student`、`edit` 或 `eef`；执行短段后丢弃剩余 proposal。
5. 获取新 RGB/本体观测，再次推理，不能继续播放旧 suffix。

必须额外保留 π0.5-only baseline。否则 Hybrid 成功时无法判断主要贡献来自 student 还是 GPT 接管。

## 开门 evaluator

旧关门判据不能直接反号照搬。第一版推开门板建议使用相对门角进展：

- episode reset 时隐藏记录 `q0`；
- 成功要求 `q - q0 >= theta_open_min` 且持续若干 tick；
- 同时要求未跌倒、没有 hard joint-limit violation；
- actor 只收到 `rollout_finished` 与最终 native outcome，不收到 q、阈值或逐步 reward。

`theta_open_min` 需要根据实际初始闭合区、相机可见范围和门资产重新标定。本文件不沿用 `-0.16 rad` 作为开门阈值。

## 实现与验收顺序

1. 在当前红块场景依次通过 UMI-4 HOLD、腕平移、腕旋转、双 DEX3 与相机可见性。
2. 用 Direct 完成红块抓取／抬升 seed task，并冻结 skill、失败分类和 evaluator。
3. 在同一四点 action schema 上训练并离线验收 humanoid π0.5，再运行 π0.5-only 和 Hybrid。
4. 把 SIMPLE 003 门资产接成同一 backend 协议，先复现旧 C0 oracle 验证资产与 evaluator。
5. 建立 `push_open_door_panel` 隐藏 evaluator并做 Direct、π0.5-only、Hybrid 对照。

## 当前阻塞项

- UMI-4 四点 SE(3)、双 DEX3、工具 schema 与记录 harness 已实现。Jᵀ 位置候选已通过一次观测锚定平移，
  但原始 ONNX、Jᵀ 候选和 6D WristPI 都尚未通过完整 SE(3) 旋转 gate。
- 头相机中红块较小，当前右腕相机严重自遮挡。
- `right_palm` site 不是已标定 TCP；DEX3 closure 不是接触/抓力。
- Jᵀ 位置候选的人工抖动窗口已启动但尚无人工结论；它在既有 Loco_manip 真机路线中已退役，不能因当前仿真位置收益直接上真机。
- 当前本地 harness 尚未注册成独立 Codex app-server，真机实时线程和 stale-plan 两阶段复核未实现。
- π0.5 尚无已训练并闭环验证的 G1 task-space checkpoint。
- SIMPLE 003 资产未证明有可动把手；首版只能验收推开门板。

## 本轮失败记录

- 两次 thread 读取请求先后因 `turnLimit>10`、`maxOutputCharsPerItem>20000` 被接口拒绝；随后按上限读取。
- 外部导入线程把工具日志封装为普通消息，`includeOutputs=false` 仍返回超长内容；改为从最终工作区规格和 runtime 快照交叉核对。
- 宽泛 `rg` 命中大量 episode 文件，噪声过大；随后限定到最终 spec、executor、status 和 GPT-as-Policy 核心 Markdown。
- 本机没有旧 `/home/galbot/lizekai/SIMPLE` 运行目录，只保留 APA 规格与快照；没有因此远程重跑或修改旧环境。
