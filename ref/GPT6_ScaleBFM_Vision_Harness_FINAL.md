# GPT-6 × ScaleBFM：视觉抓取与人形操作最终实施方案

> **主线：最小可靠接口 → GPT 视觉闭环基线 → 机器人接口 ICL → 按失败证据增加技能、记忆或小模型。**
>
> 本文面向 Codex 与机器人实施人员，整合此前仓库调查、RoboRSI 讨论和 Awesome-Astra-Embodied-AI 复核后的最终决策。当前目标不是重训 VLA，也不是预先人工完成一套通用抓取系统，而是验证：冻结的 GPT 能否通过准确、受约束、可反馈的机器人接口，利用视觉完成抓块，并把有效经验逐步转为可迁移能力。

| 项目 | 约定 |
|---|---|
| 文档版本 | FINAL v3.0 |
| 决策基准日期 | 2026-09-14 |
| 文档性质 | 架构决策、开发顺序、接口契约与实验规范；不是已完成实验的报告 |
| 首个执行平台 | 已有 MuJoCo 或 Isaac 环境，优先使用当前确实跑通 ScaleBFM 的一套，不同时迁移两套模拟器 |
| 低层控制 | 保留当前 ScaleBFM 五点控制；精确 checkpoint、link、输入、时间窗由本地审计确认 |
| 高层模型 | 冻结 GPT-6；实际 API model ID、端点和调用参数由可用性预检确认，不从产品名称猜测 |
| 首轮任务 | 自由站立、已验证可达范围内的单手抓取方块，提起并确认；随后扩展抓放、走近和双臂协同 |
| 环境信息 | 物体与环境决策信息仅来自 RGB；允许机器人自身本体感知、机器人模型与标定 |
| 最终目标 | 同一高层接口迁移到真机；仿真中不依赖物体真值或虚假附着 |
| 尚未完成的核验 | 未读取 Codex 内部线程；未连接用户主机、运行仿真或验证真机成功率 |

本版替代下列文档中与实施顺序冲突的建议，旧文件保留作为历史记录，不覆盖删除：

- `GPT6_ScaleBFM_Vision_Harness_Codex_Handoff.md`
- `GPT6_ScaleBFM_RoboRSI_Middle_Layer_Real_Robot_v2.md`

**最重要的修订：**上一版把“不调用 GPT，先做完整视觉抓取技能”列入前期验收。本版将它改为可选诊断或后续增强，不再作为 GPT 闭环试验的前置门槛。上一版确实包含这一要求；此次修改是架构决策更新，不是宣称该实验已经完成。fileciteturn24file0L175-L180

---

## 0. 一页决策：先做什么，不先做什么

### 0.1 必须先做

| 优先项 | 必须交付的能力 |
|---|---|
| 正确观测 | 新鲜 RGB、时间戳、已命名的实际机器人状态；区分当前世界与示范世界 |
| 正确执行接口 | TCP 目标转换为连续、带时间的五点参考；独立夹爪控制 |
| 实际反馈 | 分开记录请求接受、命令播放、实际到位、任务完成 |
| 最小在线闭环 | GPT 观察 → 发出有界末端／夹爪工具调用 → 本地执行 → 返回新观测 |
| 不可绕过的保护 | 单写入者、限幅、超时、取消、过时观测拒绝、已验证的稳定化机制 |
| 证据与对照 | 固定模型、控制器、接口、布局和预算，完整保存成功与失败 |

### 0.2 不作为第一版前置条件

不要求先实现 `grasp_any_object()`，不要求先加入检测器、抓取网络、视觉伺服或小 VLM，不要求先准备大量 HumanPlus 示范，也不要求先建多 agent 自演化系统。

这些模块可以非常有用，但应在最小基线暴露出具体瓶颈后分别加入，而不是同时装配后无法归因。

### 0.3 不改变的底线

**允许 GPT 直接决定下一次末端动作，不等于允许它直接控制电机、随意修改运行时、访问模拟器物体真值或阻塞低层实时循环。**

开发时允许 GPT 提议程序；正式执行使用已验证接口。生成的新程序必须经过检查和发布，不能在真机运行中在线热补丁。

### 0.4 当前最优先的研究假设

> 对简单抓块，GPT 可能已具备足够的任务推理能力；不足可能在于不了解当前机器人接口、观测坐标和实际运动响应。因此，先比较“最小可靠接口”与“最小接口＋机器人接口 ICL”，再决定是否优先增加人类任务视频或学习型中间模块。

这是假设，不是已经证明的结论。后文给出能支持或否定它的实验。

---

## 1. 调查带来的关键判断与证据边界

### 1.1 不要把“GPT＋控制器”误读为只有两个模块

Awesome-Astra-Embodied-AI 的已核对提交 `61baafd5fc94ae2db32da8da57704310033a6210` 修正了两条 G1 演示描述：Astra 做高层规划，GEAR-SONIC planner 将其转换为全身 qpos 参考，然后执行。[S01]

因此，比较应当是：

```text
对方：GPT → 某种运动规划／参考生成 → tracker → 机器人
我方：GPT → 当前适配器是否包含同等能力？ → ScaleBFM → 机器人
```

不能直接用一段演示推出 SONIC 优于 ScaleBFM，也不能把某个 planner 的全部能力归到 GPT。对方精确的视觉信息权限、抓取实现和成功统计若未公开，应记为未核验。

### 1.2 也不要过早认定 GPT 必须调用预写好的完整抓取技能

此前核对的 RoboCurve 一条 GPT-6 成功轨迹使用普通 `move_to` 及结束工具，初始 `prior_learnings` 为空；观测包含多相机和本体信息。模型通过多轮观察和末端调用组织抓放。[S02]

这支持“最小末端接口值得作为首个基线”，不证明任意人形系统都能直接成功，也不证明该实验只使用 RGB：其记录还包含关节力矩估计等本体信息，必须与本项目协议区分。

### 1.3 Harness 的收益可能来自工程闭环，而不是再加一个大模型

ASPIRE 研究执行诊断、程序修复与技能复用；RoboRSI 强调技能层级、固化代码和演化／冻结模式分离。[S05–S06]

它们可迁移的核心是：**失败留下可定位证据，改动有明确责任模块，验证后才保留。**不必照搬全部在线角色，也不应把它们默认的 RGB-D、物体接触 API 或仿真辅助机制混入本项目严格视觉结果。

### 1.4 哪些事情仍然不能声称已经做过

目前没有本项目的运行证据证明：

- 五点表示本身无法满足抓块精度；
- GPT 视觉定位必然不足；
- 一个小 VLM 是必要条件；
- 当前失败主要来自控制器、时延、TCP 偏移或 prompt；
- 当前方案已经具有真实机器人部署成功率。

用户反馈“直连没有实现目标”是事实输入；失败根因仍由本地日志决定。前两版交接同样是设计文件，而非主机或机器人验收报告。fileciteturn24file0L13-L17

---

## 2. GPT 与 ScaleBFM 之间的最终架构

### 2.1 中间层的定义

**中间层是一个本地机器人执行与实验运行时，不预先绑定“全代码”“全神经网络”或“纯 memory”。**

| 组成 | 解决的问题 | 第一版地位 |
|---|---|---|
| Harness | 观测、工具调度、权限、执行状态、日志、评估 | 必需 |
| ScaleBFM adapter | TCP／任务空间目标 → 五点参考 → 低层接口 | 必需 |
| 机器人说明与标定配置 | 单位、轴、link、夹爪、时序、边界 | 必需 |
| GPT 在线决策 | 从图像与反馈决定下一个有界动作 | 首个基线直接使用 |
| 接口 ICL memory | 记录本机命令与实际响应的关系 | 优先实验 |
| 人类视频 ICL | 任务、次序、目标关系与完成要求 | 第二类独立实验 |
| 参数化代码技能 | 固化重复有效的局部流程 | 按失败或效率证据增长 |
| 小感知模型／小动作策略 | 解决已定位的感知或局部控制瓶颈 | 后续可插拔，不先训练 |

### 2.2 在线执行链

```text
固定的能力说明、标定与任务目标
             ＋
可选接口 ICL／人类示范／已发布技能摘要
             ＋
当前 RGB、当前本体状态、最近实际执行记录
             ↓
       冻结 GPT-6
             ↓
有界工具调用，或调用已发布的可选技能
             ↓
工具验证与执行状态机
             ↓
单写入的五点参考管理器
             ↓
独立保护 → ScaleBFM → 机器人／物理仿真
             ↓
新 RGB、实际运动、跟踪误差、工具结果
             └────────→ 下一次 GPT 决策
```

这里的执行状态机只管理“请求是否可以执行、是否完成或退出”等接口事实，不意味着第一版已人工编写全部抓取阶段。

### 2.3 离线改进链

```text
开发集执行证据
       ↓
定位稳定出现的失败类型
       ↓
GPT／开发人员提出局部程序、上下文或参数候选
       ↓
权限测试、接口测试、回放、独立验证
       ↓
通过后形成冻结发布版本
       ↓
上线受监督执行；不通过则回滚
```

线上物理执行器和离线代码修改者分离。一个身体只能有一个最终动作写入者。

### 2.4 明确区分四种变量

```text
GPT proposal            模型提出的动作或技能参数
approved_reference      被运行时批准的 TCP／五点参考
low_level_command       ScaleBFM／驱动实际产生的控制
executed_state          机器人实际执行状态
```

这些字段不能统一叫 `action`。模型提议被拒绝、被缩放或未完全执行时，后续反馈和数据标签必须保留这种差异。

---

## 3. 信息权限协议：严格视觉、真实物理、可迁移真机

### 3.1 主协议 P0

**物体与环境决策信息来自 RGB；允许机器人自己的 q、qdot、IMU、实际夹爪位置、FK、URDF 和相机标定。**实验应描述为“RGB 环境感知＋本体反馈”，不要简称为完全没有其他传感信息的“纯 RGB 输入”。

由合法 RGB 计算的掩码、关键点、双目几何、视觉跟踪和不确定性允许使用，但新增感知工具要在实验中显式标记，不可暗中只增强某个对照组。

主协议不把电流／力矩／足底力等用作抓住物体的判据。若后续引入接触传感来做任务决策，单独建立 P1 传感增强协议。机器人现有保护可以使用合法自身传感，但其信息不应被包装成隐藏的物体状态工具。

### 3.2 允许与禁止

| 允许 | 禁止 |
|---|---|
| 相机 RGB、曝光时间、frame ID | 物体 `data.xpos`、free-joint qpos、真实 world transform |
| 机器人自身关节、IMU、实际夹爪位置 | GT instance mask、物体真值框、物体精确 mesh/尺寸 |
| 自身 FK 与相机／TCP 标定 | 通过场景文件、reset 参数或随机种子推算答案 |
| 从 RGB 估计的三维信息 | 将模拟器深度图伪称为 RGB 推断结果 |
| 视觉跟踪 ID | simulator body ID 作为可查询物体句柄 |
| 已验证的机器人几何与自身碰撞模型 | 用未观测的真实环境碰撞几何替演员完成规划 |
| 人类示范与合法开发日志 | 测试集布局、隐藏成功判据或测试过程反馈写回技能 |

**限制覆盖 GPT 调用的所有下游工具。**GPT 本人没有看到物体坐标，但 `grasp()` 内部读取坐标，同样违规。

### 3.3 技术隔离

建议至少分为三个进程权限域：

```text
actor / GPT bridge：只访问允许观测与白名单工具
robot runtime：物理执行、本体传感、参考管理
private evaluator：独立评分、私有 GT、测试布局
```

Actor 不持有 `env`、`MjData`、场景 USD 对象或可导入模拟器全局状态的 Python 引用。机器人自身数据从白名单关节／link 显式拣选，不能把完整 `qpos` 或 `xpos` 数组交给 actor。

初始化与评分进程可以为了运行模拟器读取物理真值，但不得把物体信息经日志、文件、错误文本或工具返回值泄漏给 actor。环境布局和 robot-only 模型文件分开提供。

API 凭据只由调用桥读取；生成程序不得访问凭据或任意网络。静态检查与进程超时是辅助措施，不应称为完整安全沙箱。

### 3.4 防止“看似成功”的物理捷径

抓取实验关闭物体 attach、weld、强制跟随、teleport、修改质量／摩擦帮助当前尝试等机制。保留真实重力、碰撞和低层动态。

限制脚部动作的第一阶段，并不等于在仿真中把机器人 root 焊死。使用固定底座臂作诊断可以，但必须单独报告，不能计入自由站立人形主结果。

独立 GT 安全监视可作为辅助研究协议，但若它根据未感知环境信息拒绝动作，其作用也是额外信息，必须单列，不混进主协议。

---

## 4. 最小工具集：不预装完整抓取能力

下列名称与字段是本项目拟议契约，不是 upstream 已存在的 ScaleBFM API。Codex 应根据现有工程实现薄适配，不假设任意仓库函数恰好同名。

| 工具 | 输入重点 | 返回重点 |
|---|---|---|
| `observe()` | 相机集合、希望晚于哪一帧 | 新图像、时间、状态、当前动作、数据新鲜度 |
| `move_tcp()` | 手臂、目标模式、参考系、观测锚点、请求 ID | 接受／拒绝、实际批准目标、命令 ID、拒绝原因 |
| `set_gripper()` | 手臂、声明单位的开度目标、请求 ID | 批准目标、实际开度、进行中／到位／超时 |
| `motion_status()` | 命令 ID | 轨迹进度、实际位姿、位置／旋转残差、超时与中断 |
| `cancel_or_recover()` | 命令 ID、已发布恢复模式 | 受控取消或稳定化的实际状态 |
| `finish()` | 模型对任务的判断与可见证据 | 仅结束模型回合；不等于私有 evaluator 判成功 |

首个基线不要求提供 `detect_object()`、`plan_grasp()` 或 `verify_holding()` 等增强工具。模型可以直接看图，提出有界动作并再次观察。需要加入时，作为可测的独立增强。

### 4.1 `observe()` 的最低返回内容

```yaml
observation_id: unique-observation-id
scene_epoch: current-reset-generation
robot_state_seq: monotonic-sequence
images:
  - camera_id: head
    frame_id: frame-identifier
    exposure_timestamp: hardware-or-mapped-time
    received_timestamp: runtime-time
    calibration_version: version-id
robot_state:
  sampled_timestamp: runtime-time
  named_proprioception: declared-fields-only
  actual_five_poses: declared-frames-and-links
  actual_tcp_poses: declared-frames
  gripper_actual: declared-units
execution:
  active_command_id: null-or-id
  state: declared-state
  observation_age_ms: measured-value
```

这是字段示意，不是可直接发送的数值实例。姿态格式、单位和时钟映射在能力契约中唯一规定。

同一观测中三相机时间可能不同，必须保留各自时间戳；不能因为打包到一个 JSON 就宣称同步。过大的时间偏差或掉帧应显式返回。

### 4.2 `move_tcp()` 的目标模式

第一版选择并固定至少一种语义清楚的模式：

```text
absolute_anchor：已声明稳定锚点中的 TCP 绝对目标
delta_tcp_at_observation：相对指定观测时 TCP 的局部 SE(3) 变化
```

不要用一个未注明含义的 `delta` 同时表示世界轴、身体轴和手轴。接口 ICL 不负责修复语义混用。

每次动作必须关联：

```text
observation_id + scene_epoch + command_id + calibration_version
```

过时观测、跨 reset 的锚点、未知坐标系或格式错误必须拒绝，不能偷偷换成当前坐标解释。

### 4.3 执行状态的划分

```text
submitted → rejected
submitted → accepted → executing → reference_finished
                                  → target_reached
                                  → timed_out
                                  → cancelled
                                  → aborted
```

`reference_finished` 和 `target_reached` 可以作为不同事件报告，而非假定它们必然同步。最终结果结构应独立保存：

```text
reference_fully_played
actual_target_reached
tracking_error_position
tracking_error_rotation
termination_reason
```

**运动工具不直接返回“物体已抓住”。**任务验证另行由合法视觉证据或独立评估器完成。

### 4.4 禁止静默“修好”模型动作

目标被限幅、投影或分段时，必须返回实际批准后的目标及原因。远超工作区的目标优先拒绝，而不是裁到边界后继续声称完成。

同一个 `command_id` 的网络重试不能重复执行物理动作。网络响应丢失时先查询执行状态，再决定是否重试。重连后不能重放过期动作队列。

### 4.5 完整动作与部分执行

第一版优先一次只允许一个活动全身运动请求；下一动作在明确状态下提交或取消前一个动作。若采用部分 chunk 执行，必须在反馈中报告已经实际执行的前缀，不能返回一个笼统的“完成”。

夹爪与手臂是否允许并发由运行时明确定义，不由模型随意并发创建冲突任务。

---

## 5. ScaleBFM 五点适配器：本项目最重要的硬接口

### 5.1 不能跳过的本地审计

记录并冻结：

| 类别 | 必填内容 |
|---|---|
| 模型 | checkpoint 路径与 hash、配置版本 |
| 五点 | pelvis、左右 wrist/hand、左右 foot 的精确 link 与顺序 |
| 坐标 | root／odom／world 定义，世界估计是否可在真机获得 |
| 旋转 | 四元数顺序、rotation-6D 排列、单位与组合约定 |
| 参考 | 当前／未来目标定义、body mask、全局或局部模式 |
| 时间 | 实际控制频率、近未来与远期 offset、buffer 行为 |
| 输出 | tracker 输出语义、驱动接口、手部独立控制 |
| 状态 | actor 使用的实际 proprio 与历史，哪些来自真机可用估计 |

ScaleBFM 的五点不是 Being 的头—手—脚表示；不要把 head 当 pelvis。论文的时间配置与真机频率仅作理解材料，现有 runtime 才决定本项目实际合同。[S04]

之前讨论出现过 400 ms 与 660 ms 的远期时间不一致线索。本版将其列为**待重新核验的历史风险**，不能断言当前仍有该错误，也不能自动选择任意一边修复。

### 5.2 TCP 到 wrist

设 `T_A_B` 表示把 B 系坐标变换到 A 系。抓取目标通常在夹持中心 TCP 定义：

```text
T_world_wrist_goal = T_world_TCP_goal @ inverse(T_wrist_TCP)
```

左右手分别标定，确认夹爪闭合轴、approach 轴和实际几何。不能直接使用 ALOHA、Franka 或他人 G1 的 TCP 常量。

FK 能给出机器人 link 位姿，但实际工具偏置、装配误差和相机标定仍需要检查。

### 5.3 相对目标必须有冻结锚点

若模型给出相对观测时 TCP 的变换：

```text
T_world_TCP_goal = T_world_TCP_at_observation @ Delta_T_TCP
```

这个目标一旦批准，不能在每个控制周期用“最新 TCP”再次相乘，否则会形成不断向前移动的追逐目标。

部署时可用短时间 odometry anchor 替代精确全局 world，但锚点有效期、更新、漂移和 reset 必须明确。实际相机变换由真实本体估计计算，不能用模拟器全局真值给演员提供额外精度。

### 5.4 五点参考不是五个瞬时数字

运行时持续维护：

```text
R = {
    target_timestamp[k],
    pelvis_pose[k],
    left_wrist_pose[k],
    right_wrist_pose[k],
    left_foot_pose[k],
    right_foot_pose[k],
    validity_mask[k]
}
```

它应依据最新实际状态、目标时刻与控制合同，转换为 ScaleBFM 的相对目标特征。参考时间使用物理时间，不把网络工具调用次数当作控制帧数。

新命令与未执行参考的衔接应处理位置、姿态和速度连续性；旋转使用自洽的 SO(3)/SE(3) 方法，不能任意对四元数分量逐项线性插值后不归一化。

### 5.5 首轮身体分工

```text
双脚：保留当前验证有效的支撑参考锚点
骨盆：已验证站姿，必要时仅允许事先验收的小范围调整
活动手：执行模型提出并被批准的目标
非活动手：保持安全参考
夹爪：独立控制与反馈
```

手部新目标不能重置另外四点。若当前姿态已经超出该模式适用范围，返回不可执行，而不是让模型继续强行前伸。

五点可达性、任务空间 IK 检查与碰撞预检查都不是动态稳定性的充分保证。第一版不让 GPT直接提出任意迈步；后续专门验收步态／骨盆协调能力。

### 5.6 与运动规划器的关系

适配器至少负责目标恢复、插值、时序和约束；复杂 loco-manip 可能另需受验证的参考规划器。

如果借用 GEAR-SONIC planner 输出 qpos，再 FK 成五点并交给 ScaleBFM，这是一个**跨控制器参考迁移实验**，必须验证其可执行性，不是把两个模块直接连接就获得同样性能。

不能在同一条执行链里同时让 IK、另一 WBC 和 ScaleBFM 各自直接给电机下命令。IK 可以用于可达性或参考生成，但执行权必须唯一。

---

## 6. 时间、标定与真实闭环

### 6.1 五个时间分开记录

```text
t_exposure：图像曝光
t_state：状态估计对应时刻
t_proposal：模型产生请求
t_apply：参考实际进入控制器
t_target：该参考希望到达的时刻
```

关键测量是 `t_apply - t_exposure`，不仅是 API latency。不同设备时钟要映射到统一时间基准；跨机 epoch 与 monotonic clock 的关系要显式保存。

不能以“同一文件中的第 N 行”代替同步。不能把包含未来观测的离线平滑状态当作部署实时输入。

### 6.2 API 等待时发生什么

ScaleBFM、驱动和执行监控继续运行，按已经批准的参考和已验证终止行为执行。GPT 断开时，可以暂时没有新的任务推理，但不得因此停止机器人稳定控制。

若需要冻结模拟器进行开发调试，应明确标记为暂停时钟诊断，不计入实时主结果。wall-clock、sim-time 和回放倍速分别记录。

### 6.3 标定验证

用实际 robot FK 将 wrist／TCP 和机器人可见部位投影回图像，检查静止、抬手、转身与小幅身体运动。

至少区分：相机内参、相机外参、动态身体变换、图像裁剪／缩放、TCP 偏置和时间延迟。静态画面投影正确不足以证明动态同步正确。

### 6.4 限值不能由文档拍脑袋固定

工作区、最大增量、速度、加速度、允许跟踪误差、图像年龄和超时由当前机器人、物体与实验范围标定后配置。

配置可以初始为空，但正式运行前所有必需安全字段必须通过启动校验；空值不得解释成“不限”。禁止直接套用手臂项目的比例限幅作为 G1 的真机安全证明。

---

## 7. 机器人接口 ICL：当前优先验证的附加信息

### 7.1 ICL 不负责猜已知的接口定义

单位、坐标、夹爪极性、link 和时间语义写入固定能力说明。让 GPT 通过试错重新发现这些已知事实既浪费预算，也不利于安全。

接口 ICL 重点描述：当前姿态下的实际运动响应、跟踪残差、有限工作区、视角变化和延迟，而不是覆盖校准配置。

### 7.2 一条接口经验包含什么

```yaml
example_id: measured-example-id
robot_profile_id: robot-and-calibration-version
context:
  before_frames: approved-rgb-references
  before_robot_state: allowed-named-fields
  posture_regime: declared-domain
request:
  tool: move_tcp
  arguments: actually-submitted-arguments
execution:
  approved_reference: actual-approved-reference
  actual_motion: measured-tcp-and-body-change
  duration: measured-duration
  position_residual: measured-value
  rotation_residual: measured-value
  restrictions_applied: recorded-restrictions
outcome:
  after_frames: approved-rgb-references
  result: reached-or-not-reached
  applicability: conditions-and-expiry
```

经验来自实际执行日志，不是模型自述。命令与实际变化分别保存。

### 7.3 少量、安全、与测试分离

第一轮可以先构造 2–5 条代表性接口示例作为设计起点，覆盖允许的小平移、必要的姿态变化和夹爪动作。数量不是已证实的最优值。

采集时不使用测试物体真值，不开放随机大范围探索。若需要估计局部图像 Jacobian，使用实际执行量；姿态或视角显著变化后重新验证有效性。

### 7.4 三类 ICL 分开报告

| 类型 | 信息 | 不应混淆的结论 |
|---|---|---|
| 任务 ICL | 人类示范、任务次序、目标关系 | 不代表学会当前机器人控制响应 |
| 接口 ICL | 工具调用与真实响应 | 不代表需要大量人类任务视频 |
| 恢复 ICL | 某类失败与有效恢复 | 不代表获得所有新任务的普适控制策略 |

不再把“人类示范＋机器人接口示例”宣称为所有任务缺一不可。它们的边际价值必须由消融验证。

### 7.5 适应成本不能隐藏

若某个方法先进行交互探测，再执行任务，探测次数、API费用、机器人时间和人工介入要单独记录，并计入端到端成本。

允许另行报告“适应后冻结”的执行性能，但要给出适应成本与适用域；不能把几十次试探之后的表现称为一次无上下文零样本调用。

---

## 8. 人类视频 ICL：在需要任务信息时加入

### 8.1 HumanPlus 的作用

HumanPlus-1000 是候选示范来源。实施时根据实际下载的 session、字段、质量和许可建 manifest，不根据名称推断完整规模。[S11]

首个任务 ICL 协议只使用有序 RGB 关键帧与相对时间；若加入身体、手部轨迹、SLAM 或标定，另列多模态示范实验。

这条路线不微调 GPT，也不依赖原生视频 API；采用显式的顺序图像输入即可。实际 API 能力仍需按官方文档预检。[S12]

### 8.2 示范编译器

可先选择约 6–12 个覆盖重要变化的关键帧，再根据预算测试数量。不要只等间隔取到大量静止帧，也不要只保留一句任务文本丢失视频条件。

示范输出包括：

```text
关键帧与顺序
示范实体与角色
抓取、提起、搬运、释放等发生了什么
当前任务的目标关系
需要满足的约束
完成与未完成的可见区别
```

从示范继承目标关系，在当前图像重新定位物体。不复制人类世界坐标、手指关节轨迹或原场景相机位姿。

### 8.3 持续上下文

请求上下文分为：

```text
固定能力说明与安全边界
固定示范／任务上下文（可选）
当前机器人与校准 profile
当前 RGB 和当前动作状态
少量近期执行记录
相关的冻结接口经验／技能摘要（可选）
```

示范帧与普通滚动观测分开存储，不能被 `image_horizon` 自动清掉。当前物体状态需要新鲜度与可见性判断，示范中的成功画面不能当作当前任务完成证据。

### 8.4 必须使用可检验 ICL 的任务

简单“抓一个明显方块”可能仅凭语言就能做，示范无效并不代表视觉 ICL 没用。

至少安排一个受控子集：同一当前场景与相同通用指令，仅示范改变“先红后蓝／先蓝后红”或“左容器／右容器”。评估器依据公开任务契约评分，不向 actor 泄漏布局或答案坐标。

对照可以包括无示范、仅终点图和时间打乱。错误示范用于观察目标依赖，不修改机器人安全说明，也不通过错误坐标／夹爪配置制造危险。

### 8.5 不把任务 ICL 与场景重建绑在一起

从人类视频理解任务，并在已经存在的仿真中执行，与从单视频重建精确几何、材质、质量和摩擦是不同项目。

第一版使用已有场景并随机化可达布局；不要让 Blender、视频重建和动态资产建模成为抓块实验的前置依赖。

---

## 9. 什么时候增加感知、伺服、代码技能或小模型？

### 9.1 按失败类型选择一个增强

| 稳定出现的现象 | 优先检查 | 候选增强 |
|---|---|---|
| 经常认错目标 | 任务描述与视觉证据 | 指点、分割、目标跟踪 |
| 动作方向正确但偏移固定 | TCP、相机、坐标约定 | 标定修复，不先加模型 |
| 目标合理但实际不到位 | 时序、可达性、五点参考、ScaleBFM | adapter 修复或受限参考补偿 |
| 接近后反复小幅来回 | 可观测性与命令—结果记录 | 局部视觉伺服、停滞检测 |
| 到位仍抓空 | 夹爪几何、接近与闭合时序 | 几何约束、视觉验证和有限恢复 |
| 成功但每步 API 等待太长 | 在线调用粒度 | 将重复有效片段固化为代码 |
| 接触行为对场景高度敏感 | 观测与反馈充分性 | 经数据验证的局部动作策略 |
| 同场景成功、新布局失败 | 隐藏常数与工作区偏置 | 当前视觉重定位，改用关系参数 |

不同时增加多个大模块后再凭成功率猜谁有效。

### 9.2 可选的局部视觉伺服

若实验确认微调阶段是瓶颈，可使用局部图像误差：

```text
e = [左右／多视图中的目标—夹爪偏差、方向误差、可见性相关特征]
Delta_e ≈ J @ Delta_xi_executed
Delta_xi = -eta * solve(J.T @ J + lambda * I, J.T @ e)
```

使用真实执行增量估计 J，限制更新幅度和适用姿态域。奇异、遮挡或多视图不一致时返回不确定并重新观察，不能输出任意大修正。

这只是候选控制实现，不是一个已经证明适用于当前机器人所有姿态的控制律。单张未标定 RGB 不能保证辨识绝对尺度与高度，应允许主动观察或多视图，而不是让大模型补写自信数字。

### 9.3 代码技能应是闭环程序，不是成功轨迹回放

一个发布技能定义为：

```text
进入条件 + 反馈策略 + 完成／失败／未知条件 + 不可改约束 + 有限恢复
```

例如 `visual_block_pick` 只有在接近、闭合、提起、验证等链条已获得有效证据后才发布。

固定坐标回放不算可迁移技能；由当前合法观测计算参数、支持失败返回的程序才具备复用意义。

### 9.4 小模型的准入条件

仅在以下情况考虑：已定位明确瓶颈、已有实际执行数据、比代码或现成感知模块更有预期收益，并能在同一接口下评估。

定位／目标选择困难可用专门视觉模块；局部控制慢或不稳定可训练：

```text
RGB history + proprio history + skill goal → bounded TCP / five-pose correction
```

这更像局部 visuomotor policy，不必再训练完整小 VLM。小策略保留同一动作审批、参考管理和保护接口，不直接绕过 ScaleBFM 控制电机。

训练数据区分建议、批准、执行及结果；不能将所有 GPT 原始提案当作专家动作。

---

## 10. Memory、技能发布与 RSI 的边界

### 10.1 四种存储，不建无限对话堆

| 存储 | 内容 | 更新方式 |
|---|---|---|
| Working state | 当前目标、帧、命令与误差 | 每轮刷新，过期作废 |
| Demonstration context | 人类关键帧、任务关系 | 本 episode 固定或显式更换 |
| Embodiment experience | 测得的接口响应、适用域 | 开发验证后冻结；测试不持久写回 |
| Skill library | 参数化代码、依赖、验证范围 | 版本发布与回滚 |

机器人标定、安全限制和控制器配置单独管理，比检索文本优先级更高。发现冲突先拒绝动作或报告，不能由语言记忆覆盖硬配置。

### 10.2 外部改进，不改 GPT 与 ScaleBFM 权重

允许改：上下文组织、检索、代码技能、故障处理、被批准范围内的参考生成策略。

禁止进化 agent 改：安全边界、物理参数帮助当前任务、观测权限、测试布局、评分器或任务成功定义。标定更改走独立校准与回归流程。

```text
开发执行 → 定位最早负责的失败节点 → 最小 patch
→ 单元测试 → 验证集配对测试 → 冻结发布
```

保留多个版本并记录失败，不根据一次成功就自动提升。

### 10.3 线上与开发角色

线上第一版不需要 Manager/Planner/Engineer/Reviewer 四个模型串行审批每个运动。一个执行者足够。

可在离线保留工程与审核职责分离：谁提出修改、谁检查证据、哪些测试通过、谁批准真机运行都记录。RoboRSI 的角色与冻结评估机制是参考，不应被理解为必须复制全部进程。[S06]

### 10.4 发布包

```text
skills/<skill_name>/
  SKILL.md          输入、范围、依赖、退出条件
  policy.py         可执行闭环
  manifest.json     代码、控制器、模型、校准与数据来源版本
  tests/            接口与已知失败回归
  evidence_index/   验证证据索引；不向 actor 暴露测试 GT
```

公共评价标准仍由独立评估器决定。候选技能可声明进入条件与预期效果，但不得自行放宽最终成功定义。

---

## 11. 真机部署：现在就按真实时间和权限设计

### 11.1 真机开机前置条件

以下任一项未完成，不进入自主真机试验：

```text
真实相机与本体时间可核对
TCP、坐标、夹爪极性已验收
ScaleBFM 本身在目标姿态下稳定
工作区与运动限值已配置
动作取消与通信故障行为已验证
单写入与请求去重已验证
人工急停、试验区域与必要防跌措施就绪
```

使用轻软物块、低风险布局、受限动作和人工监督开始。这些是试验防护措施，不是系统已通过安全认证的声明。

### 11.2 断网不是简单停扭矩

对双足系统，“GPT 没回复”不应触发无条件断扭矩，也不应冻结任意摆动中姿态。

通信失败由独立保护调用当前控制器已验证的稳定化、受控取消或人工接管路径。若尚无验证过的失联行为，真机自主实验阻塞。

### 11.3 新版本上机

先仿真与回放，再 shadow 记录建议而不执行，之后小规模受监督执行。高层生成程序不能直接热改校准、驱动或安全限幅。

只换 robot backend 不保证 sim-to-real：时延、图像、定位误差、夹爪接触、相机运动和控制响应都应重测。

### 11.4 视觉成功验证

模型可以判断成功，但必须保存可见证据。抓取验证重点是多帧物块—夹爪共同运动，以及物块相对支撑面／背景的离开。

遮挡时返回 unknown，允许重新观察。夹爪闭合、RPC 成功或一次高位姿截图都不足以单独证明稳定抓住。

真实评测可使用独立外部录像与人工评分；若使用额外追踪器作为评分真值，它必须与 actor 隔离。

---

## 12. 实验设计：最小基线、接口 ICL 和按需增强

### 12.1 公共前置检查，不计作任务能力

所有组共享相同的正确标定、接口语义、安全边界和基本执行反馈。不能通过故意不给基线正确单位或夹爪极性来制造 ICL 提升。

先做无任务的机器人接口小运动测试；这不要求先完成一套无 GPT 视觉抓取技能。

### 12.2 核心实验：2×2 ICL 因子

| 组别 | 最小可靠闭环 | 接口 ICL | 人类任务 ICL |
|---|---:|---:|---:|
| A | 是 | 否 | 否 |
| B | 是 | 是 | 否 |
| C | 是 | 否 | 是 |
| D | 是 | 是 | 是 |

在开发／验证集确定主要失败后增加 E 组：在选定基线之上只加入一种增强，例如局部视觉伺服、专门定位或已发布代码技能。

若要比较完整 RSI，另开发展与冻结测试两阶段，不把测试过程中改代码的累计覆盖称作冻结成功率。

### 12.3 任务与布局

首轮使用站立、单块、可达范围内的抓取。之后增加放置，再安排能检验任务 ICL 的次序／目标变更子集。

一个可选的试验规模起点是：10 个开发布局、10 个验证布局、30 个固定测试布局／组。它仅用于初期诊断，不是足够证明广泛泛化的统计保证；真机规模按安全和预算另设。

不按单一成功视频挑选测试样本。布局、物体姿态、视角和光照变化分层记录，避免只测位置变化后笼统宣称跨域泛化。

### 12.4 公平预算

在实验 manifest 中预先固定：

```text
model_id、endpoint、reasoning设置
相机与合法观测集合
控制器、adapter、校准版本
最大 wall-clock、GPT调用、运动请求、恢复次数
每次动作的限幅与时间约束
接口适应示例数量、来源与采集成本
成功判定方式与评分版本
```

预算数值应通过开发集预估后冻结；本文不将任意次数写成真机通用安全阈值。

代码技能能减少 GPT 调用，但也要比较物理交互次数、总运动时间和恢复次数。不能只固定云端调用上限，让一个技能内部无限尝试。

### 12.5 报告指标

| 类别 | 必报指标 |
|---|---|
| 任务 | 首次抓取尝试成功、整个 episode 成功、有限恢复后成功 |
| 时间 | 总墙钟时间、物理运行时间、API等待、完成动作时间 |
| 成本 | API调用、token、执行请求、接口适应与开发成本 |
| 运动 | 位置／旋转残差、参考边界跳变、动作被裁剪／拒绝次数 |
| 观测 | 图像年龄、跨相机时差、掉帧、重复帧 |
| 可靠性 | 超时、取消、queue underflow、基础设施故障、人工介入 |
| 判断 | 成功误判、unknown比例、失败类型 |

“首次尝试”指物理抓取接触／闭合尝试，不要求只调用一次 GPT。不同随机种子上重新 reset 的 episode 与同一 episode 内恢复分开统计。

成功率报告置信区间，配对比较保留每个布局结果。同时报告排除基础设施错误后的策略表现，以及包含全部运行故障的端到端完成率。

### 12.6 判别规则

| 结果 | 下一步 |
|---|---|
| B 明显优于 A，C 增益小 | 优先接口适应与执行经验 |
| C/D 只在目标／顺序任务改善 | 将视频 ICL 定位为任务条件，不混称运动精度学习 |
| A 能完成但很慢 | 固化重复有效片段，减少 API 粒度 |
| 目标正确但实际不到位 | 修 adapter、时间和 tracker，暂不加新视觉模型 |
| 实际到位仍抓空 | 查 TCP、夹爪几何、闭合时序和视觉判定 |
| 固化技能只在开发集有效 | 去除布局常数，重新验证适用域与感知条件 |
| 五点 oracle 也无法稳定跟踪 | 控制器／动作接口问题优先，不用更大 GPT 掩盖 |

“明显”由样本量、配对结果与置信区间解释，不把一两次偶然成功当决定性证据。

---

## 13. 实施里程碑与停止条件

### M0：只读预检与接口审计

检查当前工程、已有服务、ScaleBFM 运行方式与仿真后端；不训练新模型，不启动真机，不改现有控制器。

交付：

```text
PRECHECK.md
REPO_MANIFEST.json
CAPABILITY_CONTRACT.md
OBSERVATION_POLICY.md
CALIBRATION_MANIFEST.json
TIME_CONTRACT.json
BLOCKERS.md
```

缺失的 checkpoint、link 或频率从代码与配置寻找；找不到则明确列阻塞，不根据论文默认值猜。

### M1：最小工具与无任务执行验证

实现 observe、bounded TCP、gripper、status、cancel、finish。验证微小动作、坐标变换、脚部参考保持、实时调度与日志。

不要求人工先写完整抓取程序。模型暂未接入也可以验收工具，但不把工具验收当抓取成功。

### M2：GPT 最小视觉闭环基线 A

只使用准确的能力说明、当前图像与基本执行反馈，让 GPT 自行组织有界动作。完整保存成功和失败。

不在这一轮悄悄加 `grasp`、GT检测器或隐藏运动专家来提高分数。

### M3：接口 ICL、任务 ICL 受控比较

按 A/B/C/D 配对试验，记录适应成本。测试冻结经验库；episode 内可以读取自己的历史，但不跨测试 episode 写回持久能力。

### M4：最小局部增强与技能固化

根据验证集失败分布增加一个模块。开发候选通过权限／接口测试与独立验证后发布。失败则回退。

### M5：真机迁移

同一工具语义、不同 backend。先重新标定与安全验收，再做受监督站立抓取。禁止在线热改。

### M6：真正 loco-manip

只有 M5 足够可靠后，增加走近、停稳、骨盆调整和双臂配合。先验证每种身体模式，再由 GPT 组合；所有身体动作仍通过一个全身参考调度器。

### 停止条件

发现物体真值泄漏、物理附着辅助、时间合同不一致、无法安全取消、持续明显跟踪异常或身体失稳时，停止当前能力实验并先修复。不能通过加大 prompt、隐藏失败或放宽判据继续累计“成功”。

---

## 14. 推荐工程结构与关键测试

以下目录是拟新增组织，不代表已有文件。Codex 应复用当前工程对应模块，避免创建第二套竞争的控制服务。

```text
vision_robot_harness/
  contracts/
    observation.py
    tool_requests.py
    tool_results.py
    capability_contract.md
    protocol_policy.yaml
  runtime/
    single_writer.py
    command_state_machine.py
    reference_buffer.py
    watchdog.py
    trace_writer.py
  adapters/
    scalebfm_five_pose.py
    gripper.py
    frames_and_tcp.py
  backends/
    existing_sim_backend.py
    real_robot_backend.py
  agents/
    gpt_bridge.py
    context_builder.py
    interface_icl.py
    demo_context.py
  optional_modules/
    target_tracker.py
    visual_servo.py
    published_skills/
  evolution/
    propose_patch.py
    validate_release.py
  evaluation/
    manifests/
    actor_visible_protocol.py
    private_scorer.py
  tests/
    unit/
    integration/
    protocol/
  reports/
```

### 测试名称与意义

| 拟新增测试 | 验证内容 |
|---|---|
| `test_tcp_wrist_roundtrip` | TCP↔wrist 转换正确 |
| `test_pose_conventions` | 左右、单位、旋转约定、绝对／相对往返 |
| `test_relative_goal_anchor_is_frozen` | 相对目标不会每个周期重新叠加 |
| `test_five_pose_order_and_mask` | 五点顺序、link、有效性与归一化 |
| `test_support_anchors_not_reset` | 更新手部不重置脚和骨盆 |
| `test_reference_time_contract` | 近远期目标按物理时间选择 |
| `test_stale_observation_rejected` | 过时图像和跨 reset 锚点拒绝 |
| `test_command_idempotency` | 重试不重复执行 |
| `test_actual_arrival_not_acceptance` | 发送成功不当到位 |
| `test_partial_playout_reported` | 部分执行量被如实反馈 |
| `test_physics_runs_during_api_wait` | API等待不暂停仿真／控制 |
| `test_single_body_writer` | 并发请求不会竞争低层执行 |
| `test_no_object_oracle` | actor与工具无法读取物体真值 |
| `test_no_hidden_depth_or_attach` | 协议与物理机制审计 |
| `test_demo_context_persistence` | 示范不被普通历史裁剪删除 |
| `test_finish_not_success` | 模型结束与评分器分离 |
| `test_frozen_eval_no_writeback` | 测试期间不新增持久技能或经验 |
| `test_failure_safe_path` | 超时与中断走已验证退出路径 |

测试名描述目标；不能仅创建同名空测试就记为通过。进程隔离与权限审计也不能完全被几条单元测试替代。

---

## 15. 仓库阅读顺序：一个运行时，按需借鉴机制

| 顺序 | 项目 | 先读／先取什么 | 不要默认继承什么 |
|---|---|---|---|
| 1 | Inspect Robots [S03] | agent与embodiment分离、move工具、实际执行反馈、日志 | 当前G1插件不等于ScaleBFM五点；默认图像／深度行为需审计 |
| 2 | ScaleBFM [S04] | 现有控制合同、参考时间、状态、真机调度 | 不照抄别人checkpoint的维度与窗口 |
| 3 | RoboCurve [S02] | 一条完整tool trace；最小工具闭环 | 双臂结果不等于人形结果；力矩等额外观测另标 |
| 4 | RoboRSI [S06] | skill层级、代码固化、冻结评估、故障归因 | 深度、附着辅助、全套多agent在线循环 |
| 5 | ASPIRE／CaP-X [S05/S07] | 原子工具、执行诊断、候选修复 | RGB-D或特权感知路径 |
| 6 | Show-Harness [S08] | 小增量动作与解释器，作为局部增强参考 | 不把论文不同训练设置当同一基线 |
| 7 | ENPIRE [S09] | 真机实验、重置、验证与代码策略改进 | 不在本阶段引入完整BC/RL训练飞轮 |
| 8 | ReKep [S10] | 若需关系约束与优化，再读solver与真实感知边界 | 仿真GT keypoint/mask/SDF |

第一版默认沿用 Inspect 作为候选运行框架；若当前 Codex 已有可靠最小运行时，优先做薄适配，而不是为了名称一致推倒重写。

不在一个在线循环里套 Inspect＋RoboRSI＋ASPIRE 三套调度器。成熟框架的价值在接口和机制，不在安装数量。

### 接入前必须复核的上游细节

- 模型 API 是否支持当前消息、图像和工具参数；凭据与额度正常；模型 ID 记录在 manifest。
- Inspect 的图像历史、深度、插值速度、部分 chunk 执行与重规划默认值。
- 当前机器人后端是否已经绑定某种 action layout，不能把同维向量直接当另一种动作。
- RoboRSI、ASPIRE 的工具是否读取深度、接触或GT；是否含仿真附着。
- 引入原生代码执行时是否暴露 simulator 对象、文件、网络或凭据。

本轮最终文档是对既有调查的整合，未重新遍历所有上游仓库最新内容。实施时 pin 所用 commit，不把动态 main 分支视为已审计发布。

---

## 16. 给 Codex 的执行指令

> **本轮任务：先做 M0、M1 与 M2 的最小闭环，不训练新模型，不先实现完整抓取技能，不改 ScaleBFM 权重。**
>
> 先读取当前工程，确认已有控制器、相机、任务环境和参考接口。保留已工作的进程与环境，不在未经允许的情况下杀进程、升级依赖、覆盖实验输出或启动真机。
>
> 输出只读预检报告，写清 checkpoint、五点 link、坐标、TCP、夹爪语义、控制频率、未来目标时间、状态估计和观测权限。未确认字段列为阻塞，不猜测。
>
> 在现有后端实现最小工具：observe、move_tcp、set_gripper、motion_status、cancel_or_recover、finish。工具必须返回实际执行反馈，保持底层连续运行，并阻止过时观测、重复执行与多写入冲突。
>
> 通过无任务接口测试后，使用 GPT＋当前 RGB＋本体反馈进行站立抓块基线。暂不提供完整 grasp 技能，暂不加目标真值、隐藏抓取网络或新的视觉伺服。
>
> 收集失败类型，再比较接口 ICL 与任务 ICL。哪类失败最稳定，就只增强对应模块。新增代码经验证后才作为技能发布；不在真机在线热改。
>
> 每轮交付 manifest、完整工具轨迹、图像、实际运动与误差、任务结果、API与控制时间、阻塞及偏离。不得只交成功视频；不得宣称尚未运行的实验通过。

这是一份实施指令，不是自动授权真机运动。真实硬件启动、测试范围与安全安排仍需用户明确批准。

---

## 17. 最终验收：交付一套可解释的系统，而不只是一段视频

首个最终交付至少包含：

| 产物 | 应说明什么 |
|---|---|
| `FINAL_CAPABILITY_CONTRACT.md` | 模型能观察什么、调用什么、不得做什么 |
| `FROZEN_MANIFEST.json` | 模型、代码、控制器、标定、提示与实验版本 |
| `BASELINE_REPORT.md` | 最小闭环是否能抓；失败属于哪一层 |
| `ICL_ABLATION_REPORT.md` | 接口与任务ICL分别改变了什么 |
| `TRACE_INDEX.json` | 全部成功／失败证据的位置与完整性 |
| `REAL_ROBOT_READINESS.md` | 目前是否满足真机条件；哪些阻塞尚未解决 |
| 可选技能发布包 | 仅包含经过独立验证的增强，不虚构通用能力 |

**判定成功的标准是：**在固定权限与预算下，合法观测支持动作，动作接口可追溯，任务结果可独立确认，新布局上的表现可重复，延迟或故障不会使系统失去基本执行管理。

**总原则：先暴露准确的能力与反馈，让 GPT 在其中尝试；再按证据生长技能、记忆和小模型。**

---

## 参考资料与核验范围

正文中的 `[Sxx]` 对应下列来源。链接作为实施阅读入口，不能代替固定 commit 的代码审计。公开作者自述、演示、代码和本项目实测是不同证据等级；本文没有产生新的机器人实测结果。

### S01｜Awesome-Astra-Embodied-AI 及 planner 修订

- 仓库：`https://github.com/zjwzcx/Awesome-Astra-Embodied-AI`
- 已核对修订：`https://github.com/zjwzcx/Awesome-Astra-Embodied-AI/commit/61baafd5fc94ae2db32da8da57704310033a6210`
- 用途：识别不同工作流，提醒不能漏算 GEAR-SONIC planner；汇编不是穷尽审计或标准化benchmark。

### S02｜RoboCurve GPT-6 评测及完整轨迹

- 页面：`https://openai.robocurve.org/gpt-6-astra/`
- 已讨论的轨迹：`https://openai.robocurve.org/gpt-6-astra/runs/transcripts/rig-1_6b47f3c6.html`
- 用途：普通末端工具与反馈也可组织抓放；任务精度、耗时及额外本体观测须分别看待。

### S03｜Inspect Robots

- 仓库：`https://github.com/robocurve/inspect-robots`
- 入口：`plugins/inspect-robots-agent/README.md`
- 用途：agent、embodiment、实际执行报告、日志、先验经验配置与安全审批结构。默认值需接入前复核。

### S04｜ScaleBFM

- 论文：`https://arxiv.org/abs/2607.15163`
- 用途：稀疏身体目标、时间条件、参考缓存与状态反馈；用户具体runtime必须本地核验。

### S05｜ASPIRE

- 仓库：`https://github.com/NVlabs/ASPIRE`
- 论文：`https://arxiv.org/abs/2607.00272`
- 入口：`AGENTS.md`、`aspire/sim/.claude/libero/api-reference.md`、fix-loop相关文档。
- 用途：执行诊断、修复、技能和评估；默认几何工具并非严格RGB。

### S06｜RoboRSI

- 博客：`https://lab.noematrix.ai/blog/2-roborsi/?lang=zh#architecture`
- 仓库：`https://github.com/nssmd/RoboRSI`
- 已讨论树引用：`ae2bc840f02ff85ca18eac9766bfeeb0f0a381cf`
- 入口：`docs/architecture.md`、`docs/real-robot-tool-spec.md`、`docs/EVALUATION.md`。
- 用途：任务—技能组织、固化、角色分工、冻结评估。开发文档中的传感依赖与仿真辅助应逐路径审计，不能对全部实验过度推断。

### S07｜CaP-X / CaP-Agent0

- 仓库：`https://github.com/capgym/cap-x`
- 用途：原子工具、代码策略、执行反馈；区分不同信息权限档。

### S08｜Show-Harness

- 仓库：`https://github.com/showlab/Show-Harness`
- 用途：小增量行动、机器人解释器、历史和恢复。不是当前工程已适配ScaleBFM的证明。

### S09｜ENPIRE

- 仓库：`https://github.com/NVlabs/ENPIRE`
- 论文：`https://arxiv.org/abs/2606.19980`
- 用途：真实实验闭环、重置与验证；本阶段只考虑不更新GPT权重的分支。

### S10｜ReKep

- 仓库：`https://github.com/huangwl18/ReKep`
- 用途：关系约束与闭环规划；公开demo中的真值感知必须替换后才能用于本项目主协议。

### S11｜HumanPlus-1000

- 数据：`https://huggingface.co/datasets/humanplus-ai/humanplus-1000`
- 用途：人类视频与可选多模态示范；按实际可用session、字段与许可使用，不推断已下载规模。

### S12｜OpenAI API 官方入口

- 模型：`https://developers.openai.com/api/docs/models/gpt-6-astra`
- 工具调用：`https://developers.openai.com/api/docs/guides/function-calling`
- 用途：实施前核验endpoint、model ID、图像与工具能力；本文不提供未经验证的具体网络请求代码。

### S13｜S1 与 GEN 系列：示范条件设计参考

- S1：`https://www.skild.ai/blogs/s1`
- GEN-0：`https://generalistai.com/blog/gen-0`
- GEN-1.5：`https://generalistai.com/blog/gen-1.5`
- 用途：任务示范、跨本体语义和异步执行的设计启示；不将此前训练过的机器人策略等同于通用GPT仅靠prompt获得的控制能力。

---

**最终执行顺序：接口与反馈正确 → 最小GPT闭环 → 接口ICL与任务ICL对照 → 按失败补模块 → 冻结技能 → 受监督真机 → 扩展loco-manip。**
