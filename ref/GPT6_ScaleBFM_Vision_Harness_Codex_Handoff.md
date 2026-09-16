# GPT-6 + ScaleBFM 视觉抓取：仓库、方法与 Codex 实施交接

核查日期：2026-09-14。

本文是研究与实施设计，不是已经跑通的代码或实验报告。未读取到 `codex://threads/01a0a07a-b7a8-70f2-910f-f7710bd9fe98` 的内部内容，也未连接用户机器人或运行仿真。当前项目约束以用户本轮明确内容为准：冻结 GPT-6；使用现有 ScaleBFM 五点控制；物体信息不能来自仿真特权状态；目标为视觉闭环抓方块，并加入人类视频 ICL 与外部 harness/skill 改进。

## 0. 建议的主线

**一个运行时，三个可迁移方法，而不是同时安装四套相互重叠的控制系统。**

- 运行时首选：Inspect Robots 的 agent、embodiment、日志与评估接口。
- 原子工具与反馈设计：CaP-Agent0 / Show-Harness。
- 失败分析、可复用技能与验证后升级：ASPIRE。
- 当前机器人适配：自行实现 ScaleBFM five-pose adapter，保留原低层控制器。
- ICL：将短人类示范转换成持续保留的任务、阶段、目标约束及关键帧上下文；同时提供少量真实执行过的机器人工具示例。
- 不在第一版引入 VLA 微调、GPT 权重更新、视频生成模型或新的全身 RL 训练。

第一目标是站稳状态下抓起可达范围内的方块；先证明纯视觉抓取链路，再引入走近桌子、转身、双臂协同及跨场景泛化。

## 1. 已核查的仓库及证据等级

以下不是整个 GitHub 的穷尽目录。`有源码` 不表示已在用户环境验证，`有 G1 支持` 也不等于已有 ScaleBFM 五点适配。

| 项目 | 来源与状态 | 可以复用 | 关键限制 |
|---|---|---|---|
| Inspect Robots | https://github.com/robocurve/inspect-robots；真实 GPT-6 双臂测试对应的开源 harness | 模型工具调用、动作审批、观测、日志、任务评分、embodiment 插件 | 当前 G1 适配为站立双臂，不能冒充完整五点 ScaleBFM；API 仍在演进，必须固定版本 |
| ASPIRE | https://github.com/NVlabs/ASPIRE；NVIDIA 研究代码 | 执行轨迹诊断、技能修复、技能库、候选搜索、验证后升级 | 默认几何抓取工具使用 RGB-D；Python trial isolation 不是完整安全沙箱 |
| CaP-X / CaP-Agent0 | https://github.com/capgym/cap-x；ICML 2026 | 不训练权重的代码策略、视觉变化反馈、原子工具、跨任务技能 | benchmark 有特权状态档和感知工具档，后者常用 RGB-D；不能统一称作 RGB-only |
| ENPIRE | https://github.com/NVlabs/ENPIRE；NVIDIA 真机闭环实验 | 重置、校验、执行、反馈、改进的实验组织；双臂 YAM | 既支持代码策略也支持 BC/RL；本项目只用无梯度路线，重置与验证器需独立建设 |
| Show-Harness | https://github.com/showlab/Show-Harness；2026-09 预印本与代码 | 小增量动作、机器人解释器、动作历史、恢复插件 | 各本体仍需适配；冻结大模型路线与微调小模型路线应分开报告 |
| HumanCLAW | https://github.com/Human-CLAW/HumanCLAW；Meta 等研究团队 | 人形高层技能、任务进度、短上下文结果验证 | 半物理仿真抽去了部分低层运动困难，不能作为动态 ScaleBFM 抓取的直接证明 |
| Strands Robots | https://github.com/strands-labs/robots | Robot 接口、agent tools、仿真与真实后端组织 | 是 Inspect 的替代运行时，不建议首版二者叠加；支持列表不等于任务成功率 |
| ReKep | https://github.com/huangwl18/ReKep；CoRL 2024 | 关键点关系约束、子目标和路径优化 | 公开仿真示例使用 GT 关键点/掩码跟踪和 SDF；严格视觉实验必须替换 |
| VoxPoser | https://github.com/huangwl18/VoxPoser；CoRL 2023 | 语言到空间代价图、闭环运动规划 | 公开 RLBench 示例使用 oracle mask，不可直接宣称无物体特权 |
| Code as Policies | https://code-as-policies.github.io/；ICRA 2023 | 通过现有感知和控制 API 合成带循环的程序 | 抽象 API 必须真实实现，不能把 get_object_pose/pick 的隐含能力忽略 |
| GPT-Policy-Eval | https://github.com/cheng-haha/GPT-Policy-Eval | 一段视频提示的真实机器人案例，可作观察资料 | 当前核对内容主要为 README、视频和素材，不能当作完整可执行 harness |

发现更多案例可查，但不能以汇总替代原始实现审计：
- https://github.com/zjwzcx/Awesome-Astra-Embodied-AI
- https://github.com/kairunwen/Awesome-Robot-Use-Agent

### 1.1 最直接的 GPT-6 证据

RoboCurve： https://openai.robocurve.org/gpt-6-astra/

双臂 YAM 的方块入碗测试为 19/20，拼图插入为 2/20；方块任务平均约 2.5 分钟。每轮给模型三路相机和 proprioception，通过绝对末端位姿及夹爪工具调用，IK/执行接口负责运动。样本小、评分非盲且部分模型使用不同 rig；这不是高频端到端动作生成的证明，也不是 ScaleBFM 的直接复现实验。

### 1.2 仓库阅读入口

Inspect Robots：
- `plugins/inspect-robots-agent/README.md`
- `plugins/inspect-robots-capx/`
- `plugins/inspect-robots-isaacsim/`
- `src/inspect_robots/`
- `tests/`

ASPIRE：
- `AGENTS.md`
- `aspire/sim/CLAUDE.md`
- `aspire/sim/.claude/libero/CLAUDE.md`
- `aspire/sim/.claude/libero/api-reference.md`
- `aspire/sim/.claude/libero/fix-loop/QUICKSTART.md`
- `aspire/sim/.claude/libero/fix-loop/INSTRUCTIONS.md`
- `aspire/sim/.claude/libero/fix-loop/SKILL.md`
- `aspire/real/AGENTS.md`
- 已学习技能快照另有 `learned-skills` 分支；读取并审计，不盲信旧场景常数。

ReKep：
- `constraint_generation.py`
- `keypoint_proposal.py`
- `subgoal_solver.py`
- `path_solver.py`
- `environment.py`：重点找 GT 获取路径并替换。

这些是研究阅读入口，不授权启动任何真机服务。

## 2. 信息权限契约：视觉不是“不允许计算几何”

第一条实验协议定义为：**物体和环境信息仅由 RGB 获得；允许机器人自身传感、本体模型和标定。**

### 允许进入 actor

- 相机 RGB、曝光时间、frame_id。
- 机器人关节、IMU、FK、实际五点状态、夹爪实际宽度等自己可测状态。
- 已标定相机内外参、URDF、wrist-to-TCP 固定变换、夹爪轴和极性。
- 由合法 RGB 计算出的掩码、关键点、视觉跟踪、双目/多视图重建与不确定性。
- 当前任务指令、示范关键帧、由合法日志产生的技能记忆。

### 禁止进入 actor，包括它调用的所有工具

- MuJoCo 物块 `data.xpos`、物体 free-joint qpos 或 Isaac 物体 world transform。
- GT instance segmentation、GT object bounding box、GT object mesh/size/pose。
- 随机化种子、布局参数、重置脚本中的物块坐标。
- 从仿真接触直接读取的“已抓住”标志，若实验仍声称物体信息只有视觉。
- 读取这些值的 `get_object_pose()` 或 `grasp()`，即使 GPT 本人看不到原数组。
- 对仿真进程 unrestricted Python import、内存访问或包含布局配置的文件系统。

RGB-D 可另设第二协议，不得把深度工具链结果写成 RGB-only。由 RGB 估计的深度与传感器深度也要注明差别。评估器可以独立使用 GT，但测试期间不得回传给 actor，且不能被 RSI 修改。

建议 actor 与 simulator process 分离，通过显式 RPC 白名单连接。单纯提示“不要读取 GT”不足以阻止意外泄漏。静态检查、进程超时不是完整安全沙箱。

每个估计必须带 provenance：输入帧、时间、算法、坐标系、置信度。`object_track_id` 是视觉跟踪 ID，不是 simulator body ID。

## 3. 系统分层

```text
人类视频 → 关键帧/目标关系/阶段 → 持续保留的 demo context
                                              │
当前 RGB + proprio → 观测摘要/合法视觉估计 ─────┤
                                              ▼
                         冻结 GPT-6：选目标、选工具、诊断与重规划
                                              │
                         有界原子工具 / 经验证的参数化技能
                                              │
                         视觉闭环伺服 + 时序轨迹解释器
                                              │
                         ScaleBFM 五点参考 + 独立夹爪控制
                                              │
                              物理执行 → 新观测 → 结果验证
                                              │
                     开发阶段：失败日志 → patch → 测试 → 技能库
```

远端 API 不进入低层实时循环。网络等待期间，ScaleBFM 的既有实时调度继续运行，保持或安全地完成当前批准参考。不能为了等待 API 偷停物理时钟，再把结果叫实时部署。分别记录 wall-clock、sim time、API latency、命令年龄和执行速度。

## 4. 工具接口：先实现能力，再把名字交给 GPT

以下是本项目拟新增接口，不是 upstream 已有的 ScaleBFM API。

| 工具 | 输入/输出要点 |
|---|---|
| `observe(cameras, since_frame)` | 返回新 RGB、时间戳、本体状态；重复旧帧需明确标记 |
| `track_visual_target(description, frame_id)` | 返回 RGB 产生的 track/mask/keypoint/confidence |
| `estimate_geometry(track_id, frame_ids)` | 可选；只使用合法多视图/标定推断，失败时返回不确定而非编造坐标 |
| `move_tcp_delta(arm, delta, frame, observation_id)` | 有界末端增量，由 adapter 转五点参考；拒绝过时观测 |
| `set_gripper(arm, width)` | 单位、范围、极性显式，控制与实际宽度分开 |
| `poll_motion(command_id)` | 返回实际跟踪误差、完成/超时/拒绝，不把 RPC accepted 当到位 |
| `verify_visual(predicate, frame_ids)` | 至少返回 satisfied/violated/unknown 与证据帧 |
| `retrieve_skill(task, phase, failure)` | 返回参数化经验，不返回当前场景秘密坐标 |

`grasp(object)` 不得作为首版假想原子工具。它只能在接近、对齐、闭合、提起、验证、恢复这些原子链条实际跑通后，封装成可复用技能。

### Inspect 特别要改的默认行为

- `image_horizon=2` 会裁掉旧观测图；demo 帧必须独立保留，不能几轮后消失。
- `depth=render` 是 agent 插件的默认选项；严格 RGB 协议应关闭，并检查下游工具也不能偷偷读 depth。
- `prior_learnings` 可注入经验；每次试验记录其路径与 hash。
- `done` 是 agent 停止声明，不是抓取成功真值。
- 运动工具的 playout 与控制器 replan interval 需匹配；只播放前缀会导致持续欠跟踪。
- 上游绝对 move 工具用安全速度生成轨迹，不要向未支持 duration 的工具传一个自造参数。

## 5. ScaleBFM 适配边界

五点为 pelvis、left wrist/hand、right wrist/hand、left foot、right foot，精确 link 与手部坐标系以现有 runtime 为准。不是 head-hand-foot 的 Being 接口。

抓取规划通常在 TCP/夹爪夹持中心做，而 tracker 可能接收 wrist link：

```text
T_world_wrist_target = T_world_TCP_target @ inverse(T_wrist_TCP)
```

该变换若错误，就会产生稳定的抓取偏移；加 prompt 或示范无法从根本上修复。

第一版站立抓取：
- 支撑脚维持世界锚点；骨盆采用经过验证的站姿/小幅可达调整。
- 活动手执行视觉生成的目标；非活动手留在安全区域。
- 五点参考必须有单调时间戳和明确近/远期采样语义。
- 不要每次工具调用都把双脚、骨盆重新初始化为默认常数。
- 参考插值必须在 SE(3) 上自洽，动作限速、超时、取消与 hold 由本地执行器完成。
- 达到的是实际目标，而不是“发送成功”。

第二阶段才开放 stepping primitive。行走、双手伸展、骨盆补偿共享一个全身资源调度器；不得让两个 agent 并行发送相互冲突的身体轨迹。

## 6. 严格 RGB 的抓方块基线

### 6.1 最小闭环

1. 识别目标与干扰物，只使用 RGB。受控彩色块可先用经典视觉；SAM 等模型是可替换模块而非必须条件。
2. 从头部/腕部视角估计夹爪中心、目标边缘及对齐方向。
3. 依据标定与多视图建立粗几何；也可通过小幅主动运动获得视差。
4. 先到安全预抓位置，再由局部视觉误差驱动小增量动作。
5. 对齐后受控闭合，随后小幅提起。
6. 用连续图像验证物体相对夹爪近似固定、相对背景确实抬升。
7. 遮挡时返回 unknown，换视角，不直接报告成功。
8. 失败则先安全撤离/张开/重新定位，禁止无限原位重复闭合。

### 6.2 图像空间伺服示意

令特征误差包含两视角的夹爪-目标像素差以及方向误差：

```text
e = [du_view1, dv_view1, du_view2, dv_view2, orientation_error, ...]
```

在小范围内，根据实际执行的末端增量估计图像 Jacobian，而不是假设命令全部到位：

```text
Delta e ≈ J Delta xi_executed
Delta xi = -eta * inverse(J.T @ J + lambda I) @ J.T @ e
```

对动作幅度、轨迹速度和条件数进行限制。视角、骨盆或遮挡变化大时重新估计。局部伺服在本地运行，不每一个微小动作都等待 GPT。

这是本项目建议的轻量 RGB 方案，不是某个 repo 的已验证 G1 实现。需要充分可观测的视角/特征；单张未标定 RGB 不保证能恢复抓取高度，不能靠大模型自信补齐尺度。

RGB-D 分支可使用 ASPIRE 的 SAM3 + Contact-GraspNet；它必须独立标记协议，不能替换 strict-RGB 对照。

## 7. 视频 ICL 的实施

### 7.1 API 约束

官方 GPT-6 Astra 页面列出文本/图像输入、function calling、structured outputs；native video 与 fine-tuning 不支持。因此把示范转换成按时间排序的图片加时间标签，不使用臆造的 `input_video` 字段。

### 7.2 HumanPlus 能提供什么

数据卡：https://huggingface.co/datasets/humanplus-ai/humanplus-1000

本次可见发布是 preview，不能按名字推定完整1000小时/1000任务都已提供。条目可包含视频、标定、SLAM、全身与手部运动、置信度，但不等于拥有机器人命令或可靠物体 GT。下载前核查子集字段与许可；所见许可为 CC-BY-NC-4.0。

Strict video ICL：只给示范 RGB + 时间顺序。用来提供任务、目标关系、阶段和视觉完成条件。

Multimodal demonstration ICL：可额外使用数据中的人类轨迹和标定，得到粗几何运动模板；必须单独报告，不再称仅一段 RGB 视频。人类 wrist/head frame 不能直接复制成 ScaleBFM pelvis reference。

### 7.3 示范编译器的输出

选择约6–12个有信息的关键帧，优先覆盖：接近、对齐、首次接触、闭合、提起、放置/释放。帧数只是设计起点，需做消融。

```yaml
intent: 把示范中的目标物体抓起并放到目标容器中
entities:
  target: 依据视觉指认的目标物体
  destination: 依据视觉指认的容器
phases:
  - approach
  - align_gripper
  - close
  - lift_and_verify
  - transport
  - release_and_verify
constraints:
  - 不碰撞桌面与干扰物
  - 不把手已经闭合当作抓取成功
  - 目标坐标必须从当前观测重新估计
success:
  - 目标先与夹爪共同移动
  - 释放后位于容器中且稳定
```

不复制人类关节角；不复制原场景绝对位置；不把示范本身的成功状态当当前真实状态。

### 7.4 两类 ICL 示例缺一不可

**任务示范**：告诉 GPT 要完成什么及阶段顺序。

**机器人接口示范**：2–5个真实执行过的 `before RGB + proprio → tool args → after RGB + actual residual`，说明当前夹爪的轴、极性、TCP、单位和动作幅度。

第二类示范不是再次收集百条遥操，而是少量系统辨识/接口说明。它往往比只增加人类视频更能修复厘米级偏移。

### 7.5 持续上下文组织

每轮请求包含固定 capability contract、固定 demo keyframes、当前观测、相关技能摘要、少量最近执行记录。不要每轮重新追加完整视频与所有旧帧。

显式标记 demonstrated world 和 current world；任务目标可以继承，当前物体位置不可以继承。

同一任务语义下的场景泛化与“从单视频恢复完整物理场景”是不同目标。HumanPlus 视频本身不保证提供可直接重建 MJCF/USD 所需的全部几何、质量与摩擦。第一版使用自己已建立的仿真场景，只随机化布局并隔离初始化真值。

## 8. RSI：只改外部系统，不改 GPT/ScaleBFM 权重

可更新：技能脚本、技能检索、上下文构造、动作参数建议、故障诊断规则。

不可由进化 agent 修改：观测权限、物理引擎、任务评分、测试布局、安全上限、目标定义。标定变更应走单独版本与回归，不作为试验作弊空间。

```text
开发场景执行
   ↓
合法观测 + 请求/实际动作 + 视觉结果 + 异常
   ↓
定位具体失败类型
   ↓
生成小范围 patch
   ↓
静态/权限/接口测试
   ↓
独立验证布局上的配对评估
   ↓
通过则加入可复用技能库；不通过回滚
```

失败类型至少包括：目标认错、视角不足、图像过时、TCP偏差、不可达、动作未到位、闭合未夹住、滑脱、支撑不稳定。

技能应使用对象相对关系和在线重新定位，而不是某个种子的世界坐标。保留每个版本、来源试验、成功/失败样本及验证范围。

仅把失败写成一句“下次向左一点”是反思记忆；经过验证并持久化复用的程序/上下文改进，才是本项目所说的外部自改进。不要宣称 GPT 权重在自主递归学习。

方法依据：
- ASPIRE https://arxiv.org/abs/2607.00272：LIBERO-Pro ablation 为14%→62%→72%，分别为基线、加入执行诊断修复、再加候选搜索；不是 GPT-6/人形指标。
- ENPIRE https://arxiv.org/abs/2606.19980：把实验重置、执行、验证和改进形成循环；代码策略分支适合无微调路线。
- SHAPER https://arxiv.org/abs/2608.11350：固定 VLM，演化 skill 与 harness；本次未核验可直接复用的公开实现。
- Recursive Harness Self-Improvement https://arxiv.org/abs/2607.15524：一般 agent 外部系统改进，不能当作物理抓取成功证明。

## 9. 里程碑与对照实验

### M0：不做抓取，先把接口与权限测清

输出 `CAPABILITY_CONTRACT.md`、相机/TCP标定、观测字段白名单、固定版本 manifest。

必须通过：
- actuator不接收模型任意 Python；物块真值不可读；
- 相机帧新鲜；左右/单位/旋转/夹爪极性正确；
- 末端小位移能跟踪，脚部不会因调用重置；
- API 等待期间物理与低层继续运行；
- 请求完成与实际到位分开记录。

### M1：站立、单块、严格 RGB 闭环

不使用人类视频。先证明视觉定位→对齐→闭合→提起→验证能实现。失败优先定位感知、接口或控制误差，不盲目增加 prompt 长度。

### M2：同任务不同布局

随机物块位置和朝向、适度相机/光照变化。固定模型与工具预算，任何坐标必须从当前图像重新获取。

### M3：任务 ICL

同一场景给不同示范：换目标容器、左右手分工、先红后蓝/先蓝后红。保持语言尽量相同，以验证模型确实依赖示范。对照无示范、错误示范、仅终点图、时间打乱示范。

### M4：外部技能改进

训练/开发布局用于 patch；validation 用于选择；test 完全封存。每个版本报告相同预算下首次尝试成功率与最多K次恢复后的成功率，二者不可混报。

### M5：扩展到真正 loco-manip

增加走近、转身、骨盆补偿和双臂任务。先离线验证新的全身 primitive 能力，再交给 GPT 组合。不得把腿部碰撞/失稳藏在 kinematic teleport 或隐藏固定物体脚本里。

建议比较：

| 编号 | 设置 |
|---|---|
| B0 | GPT直接预测绝对末端目标，无工具经验 |
| B1 | 同GPT + 有界工具/执行反馈/视觉验证 |
| B2 | B1 + 人类视频任务ICL |
| B3 | B2 + 少量机器人接口ICL |
| B4 | B3 + 经过独立验证的持久技能库 |

保持相机、合法观测、控制器、动作限幅与 API/时间预算一致。报告成功率区间、首次成功、恢复成功、真实耗时、调用次数、滑脱率、误判成功率、全身异常。场景数量和显著性按实际预算确定，不能从单个剪辑宣布泛化。

## 10. 建议代码结构（新建，不是 upstream 现成目录）

```text
harness/
  contracts/observation.py
  contracts/actions.py
  contracts/provenance.py
  adapters/scalebfm_fivepoint.py
  perception/frame_bank.py
  perception/rgb_target_tracker.py
  perception/visual_servo.py
  agents/context_builder.py
  agents/demo_compiler.py
  agents/tool_planner.py
  skills/stationary_block_grasp.py
  verifiers/visual_grasp.py
  evolution/patch_validate_promote.py
  eval/private_gt_scorer.py       # actor不可导入/读取
  tests/
```

关键测试：
`test_no_object_oracle`、`test_no_depth_in_rgb_protocol`、`test_tcp_wrist_transform`、`test_world_support_anchor`、`test_frame_freshness`、`test_physics_continues_while_api_waits`、`test_actual_arrival_not_rpc_acceptance`、`test_demo_frames_remain_in_context`、`test_done_is_not_success`、`test_skill_has_no_layout_constants`。

## 11. S1、GEN-0 / GEN-1.5 的正确启示

- S1：https://www.skild.ai/blogs/s1 。视频条件机器人策略经过相应训练；不在测试时更新权重，不代表没有运动策略训练。可借鉴“任务意图、身体差异、当前进度”的示范表示。
- GEN-0：https://generalistai.com/blog/gen-0 。主线是物理数据规模与异步感知/动作，不是一个公开 GPT-harness 实现。
- GEN-1.5：https://generalistai.com/blog/gen-1.5 。与 one-shot 更直接相关，提示常为传感—动作序列，并非都只是任意人类RGB。可借鉴短示范、滚动观测与示范组合，但不可声称冻结GPT自动继承其电机策略。
- 官方 GPT API：https://developers.openai.com/api/docs/models/gpt-6-astra 。实施前复核 endpoint、model id、图像/工具支持与额度，不把网页产品名当作所有 gateway 都支持的模型别名。

## 12. 交付标准

首个可交付版本不以“能演示一次”为验收，而以以下证据为验收：

1. 代码路径证明目标几何只来自合法视觉，不读取仿真物块真值。
2. 至少跨多个未见布局，保持同一工具接口与预算完成抓取。
3. 完整图像、工具调用、实际运动和结果证据可回放。
4. 使用视频ICL时，换示范能改变目标/顺序，错示范与无示范对照可解释。
5. 使用RSI时，提升来自被验证的外部代码/上下文版本，而不是修改评分、增加隐藏信息或放宽安全界限。

**最终优先顺序：接口正确与视觉闭环 > 任务视频ICL > 可验证的技能自改进。人类视频负责定义“要做什么及怎样算完成”，机器人接口示例负责说明“这台机器怎样动”，ScaleBFM负责把合法五点参考稳定执行。**
