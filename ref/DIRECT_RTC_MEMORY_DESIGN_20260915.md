# 无示教 Direct → 可复用技能 → π0.5 + Astra

本版围绕正在运行的 RSI 四点抓取实验，区分已实现、上游事实和待验证设计。新增文件统一在 RSI；现有环境只读使用。2026-09-15。

## 1. 修正原有路线

当前问题是检验 Astra 的无示教 Direct 能力，不以示范、π0.5 checkpoint 或先抓成功一次为前提。保持 model_38000 和执行配置不变，让 GPT 从 RGB、命名机器人状态及工具回执决定下一步。失败也是有效结果，但只能说明具体的模型、提示、工具、执行器和场景组合失败，不能直接归因于 GPT 不懂几何或目标不可达。

最优的研发顺序是：先做暂停仿真的 Direct 试运行，定位系统瓶颈；随后评估持续运行的执行器与异步规划；用经验证的机器人执行数据训练视觉 π0.5；最后比较 Direct、π0.5-only、Hybrid。当前不要再训练一个小 VLM：它既不能自动修复参考跟踪误差，也会增加一个尚无合适标签的数据问题。

上一轮的“先解决所有独立门槛才花 GPT 调用”“必须先有成功示范”不再作为 Direct 入口条件。它们仍然限制结果解释和真机准入。上真机尚未授权。

## 2. GPT-as-Policy 到底做了什么

审读的公开快照：`ref/GPT-as-Policy/download_manifest.json`，commit `1e72362a85956cb8b3fc4e193729e7e6db990539`。

- [Direct SKILL](https://github.com/anonymous-report-421/GPT-as-Policy/blob/main/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md)：一个持久 agent 处理一个 episode；读 RGB 和本体状态，自选 EEF 目标，调用阻塞工具，再看实际执行。允许笔记、计算、裁图。`NOTES.md` 记录确认的进度，`history.json` 记录执行历史。没有 π0.5 提案、回滚、换场景或隐藏规划器。
- [EEF 合约](https://github.com/anonymous-report-421/GPT-as-Policy/blob/main/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md)：双 ARX X5，25 Hz，单次 1–5 控制步，即 40–200 ms。每次真实 ACK 后重算局部 DLS IK；目标与到达是两件事。其 opening 为 0 闭合、1 张开，本项目 DEX3 closure 为 0 张开、1 闭合，不能按数值照搬。
- [Direct client](https://github.com/anonymous-report-421/GPT-as-Policy/blob/main/hybrid_rollout/robodojo/robodojo_server/gpt_only_client.py)：绑定观测 request ID，逐步执行并保存实际 action/state、IK 诊断、native success 和步数。校验拒绝可以修正，物理/通信的不确定执行不能重发。
- [Hybrid context](https://github.com/anonymous-report-421/GPT-as-Policy/blob/main/hybrid_rollout/robodojo/skill/context/teacher_context.md)：复用过往成功流程的经验，但明确这个 rollout 不训练学生。每次读取新提案，分别看上一步结果与下一步意图，再决定接受还是短程纠偏。

因此可以复用的是：MD 操作契约、持久回合上下文、真实 ACK、proposal/outcome 双重检查、记录与测评组织。公开代码不足以证明“先在任务 A 自动训练出 SKILL，再自动扩到所有任务 B”的闭环已经实现。仓库是技术报告与代码，不能称为已录用顶会论文。公开分数也不是我们的 humanoid 成绩。

我们的 R017 是四点接口的最小 Direct pilot，暂时禁用 native shell/web，提供显式几何工具；它比上游 full-agent 工具集窄，不能称为逐项完全复现。后续 full-agent 对照可开放隔离的计算/裁图/笔记工作区，但不能开放环境源代码、隐藏评测状态或其他回合答案。

## 3. 中间层是什么

`RGB + 任务 + 命名本体状态 + 回合记忆 → Astra → 有界四点 SE(3)/手指请求 → 执行器 → ScaleBFM → q29/PD`。

中间层首先是 harness：让模型的意图成为有坐标、时间、权限、回执和终止语义的命令。Memory 是它的组成部分，不替代控制器。π0.5 是未来可插拔的动作生成器，不是现在必须接入的步骤。

- `four_point_translate`：对指定点进行世界系位移；只算目标，不执行。
- `four_point_rotate`：旋转向量的方向是旋转轴，长度是弧度；围绕指定 pivot 同时变换位置和姿态。
- `image_pixel_to_world_plane`：像素射线与显式标定的工作台平面相交；没有物体深度、大小或接触真值。
- `four_point_place_local_point`：将手腕局部偏置点放到指定世界位置，保持当前腕姿；偏置没有标定时只是几何假设。
- `scalebfm_act`：实际执行 GPT 的有界四点轨迹及两手开合；必须返回测量残差和状态。
- `pi05_infer`：未来学生生成待审核提案；`loco_execute` 执行通过同一契约验证的最终提案。

`move_tcp()` 中 move 是移动，TCP 是 Tool Center Point（工具中心点）。我们目前只有 wrist link 的可靠命名，没有经验证的 DEX3 抓取 TCP，所以不把 wrist 冒充 TCP。日后其参数应明确 `arm`（左右手）、`position_m`（米）、`quaternion_wxyz`（单位四元数，标量在前）、`frame`（基座/世界系）、`duration_s`（秒）、`gripper`（本项目 0 张开、1 闭合）。

四点公开顺序固定为左腕、右腕、左踝、右踝；跨模块按名字映射。关节输出仍为 model_38000 文档规定的串行 29 关节顺序。足部轨迹的存在不等于任何任意四点目标都物理可行；站立与行走分别验收。

## 4. chunk 与 RTC：分开三个时间尺度

不能用同一个 chunk 数字指代所有层。当前 GPT 的一个 waypoint 是 0.5–3 s 的运动参考；ScaleBFM 50 Hz，参考窗口 34 帧，取偏移 0/1/2/3/4/25；PD 250 Hz。R017 每次只交付一个 waypoint，结束后反馈，物理在推理时暂停。它测视觉决策和执行接口，不测真机实时性。

Direct 后续消融建议：先保留参考轨迹时长，只改变每次执行后反馈的间隔为 5/10/25 个 tracker tick（100/200/500 ms）。轨迹总时长与反馈间隔解耦；重新规划必须承接当前参考位置、速度，不能每 100 ms 把 minimum-jerk 的起点和速度都重置。接触附近优先短反馈窗口，但其收益必须以模型等待时间、跟踪误差和成功率一起判断。

真正 RTC 对应 [PI 原论文与说明](https://www.pi.website/research/real_time_chunking)：旧 chunk 执行时异步生成新 chunk，对必将执行的动作前缀施加约束，再生成可修改的剩余段。原方法用于 diffusion/flow VLA，不能对不可访问内部采样过程的 GPT 文本 API 直接套 inpainting。可以借鉴其时间戳和提交前缀原则。

对未来 π0.5 的起始设计（提案，尚未测优）：

1. 以 50 Hz 输出 H=50 的 1 s chunk，与 ScaleBFM 时间对齐；H=25/50 做对照，先不把 100 当默认。
2. 实测从图像曝光、预处理、推理到入队的端到端延迟 L，而非只报 GPU forward；提交前缀 d=ceil((L_p95+抖动余量)/0.02)。推理返回时用实际已经经过的 tick 重新对齐，禁止执行过期头部。
3. 保证 H 足够覆盖 d、剩余连续性约束区和一个可反应区；若 d 接近 H，延长 chunk 不是完整解法，应降延迟、降频或换分层架构。模型端的 overlap/execution_horizon 与控制器的执行步数分别命名。
4. 只有一个仿真/控制写者。策略线程只提交 `observation_seq, captured_at, valid_from_tick, reference_version, committed_prefix, candidate_suffix`；版本不匹配就丢弃。队列低水位提前推理，空队列进入经验证的 HOLD/撤回流程，记录 underrun。
5. 无接触自由空间可做速度/加速度约束的过渡；闭合、松开、门把接触等离散事件不可简单平均。缺少连续性条件时拒绝新计划，不能硬拼。

可复用 [LeRobot RTC](https://huggingface.co/docs/lerobot/rtc) 的 ActionQueue、RTCConfig、延迟参数、前缀条件与离线可视化；[PI Kinetix RTC](https://github.com/Physical-Intelligence/real-time-chunking-kinetix) 适合复用延迟实验方法。都需要适配本项目的动作空间，不能直接接 q29。Astra 的等待若是秒级，就做异步阶段监督或低频恢复；π0.5/执行器持续维持控制。给 Astra 的新阶段命令也必须通过版本和动作前缀检查。

## 5. history 与 memory 如何读取

零示教不等于没有回合记忆。基线允许机器人接口知识和本回合已发生的事，不允许成功轨迹范例、其他场景答案或人类视频。

- 工作记忆：最新多视角 RGB + 上一关键帧，最近 4 次请求/回执，最新四点测量/参考/误差、手指状态、剩余预算。上述“4 次”是起始消融值，比较 2/4/8，不能宣称最优。
- 摘要记忆：当前阶段；有图像证据的已完成事项；最近失败动作及实际残差；被否定的假设；下一项可观察验证；不重复的尝试。几何估计带参考坐标系、图像 ID、时间和不确定度。新图反驳时撤销完成标记。
- 事件历史：完整 JSONL 只追加，保存 request/observation ID、动作目标、实际状态、时间、结果及公开简要理由。按 ID 查询本回合证据，不能凭空生成“过去成功”。
- 跨回合 skill memory：只从开发集沉淀，字段为前置条件、适用机器人/执行配置、已验证做法、失败条件、证据路径和版本。先用简单标签匹配任务/阶段/失败类型，最多读 1–3 条，不急着引入向量库。
- 评测冻结：零示教 Direct 禁用跨回合检索；skill/ICL 方法只读冻结的开发集 memory。测试回合产生的新经验先隔离，整批评测结束后才进入下一版开发集。

这是可验证的工程学习流程，不是自动自我改进保证。R017 已有持久对话和完整工具回执，但尚未实现上述滑动图像窗口、结构化检索服务或自动 memory 提升。不能把设计写成现成能力。

## 6. π0.5 微调与 Astra 协作

先稳定同一个 reference→actual 执行映射，再积累由 GPT 自主交互产生、由真实反馈确认的数据。行为克隆的正样本取成功动作片段与恢复后的正确动作，不直接复制失败目标。失败段保留为检索/失败检测数据。到达但未抓住、夹爪闭合但未抬起分别标注，不以命令代替效果。

候选动作表示为 4×(平移3+局部旋转向量3)+双手开合2=26 维，再按所选 π0.5 实现的维度和掩码配置补齐；外部仍编译为命名四点 SE(3)。姿态在 chunk 起点的固定参考系表达，不能每帧偷偷换锚点。足部支持/动作 mask 由明确阶段协议提供。不要直接把世界坐标大范围平移当作跨场景可迁移标签。

训练输入为同步机载 RGB、语言目标/阶段、命名机器人状态和参考执行状态。不能混入 actor 不会拥有的物体位姿、接触真值或隐藏奖励。源 profile、相机与时序变化需显式分组，归一化统计仅在训练集计算。

Hybrid v1 先忠实于上游：新 π0.5 提案 → Astra 审查上一执行结果与下一意图 → 接受或替换短段 → 新反馈。Hybrid v2 才为真机改成事件触发的异步监督：进度停止、跟踪偏差持续、目标遮挡/丢失等触发 Astra。触发器最初用可审计规则；Astra 未及时返回时不让整机控制线程等待。

现有 M3 服务明确 image=None，不能当视觉 π0.5 使用。需要真的视觉输入、任务相关训练和匹配的四点动作头。没有合格 checkpoint 时标记“未接入”，而不是用服务连通冒充功能可用。

## 7. 测评与视频

先保存当前固定场景 pilot 的全部成功/失败视频；不要声称随机场景泛化。冻结后再做成对条件：Direct 无 memory、Direct + 开发集 skill/ICL、视觉 π0.5-only、Hybrid；相同任务布局、初态、控制器、预算和评测器。

记录 native success、未完成/稳定性失败/通信失败、到达/抓持/抬升阶段证据、跟踪误差、无效工具调用、回合和工具数量、曝光到计划延迟分布、执行时长和墙钟时长。连续 RTC 额外记录 queue underrun、deadline miss、切换前后速度跳变、关节速度及饱和持续时间。不能只比较剪掉规划等待的视频时长。

建议下一批开发用 5 个固定布局，冻结后评测 20 个独立布局，每个布局 3 次模型运行；小样本用成功数/总数和置信区间，不宣称可靠率。这个规模只是后续建议，尚未启动大批模型调用。

视频应含任务、方法、后端、sim/wall 时间、当前请求、执行状态。第三视角仅用于解释，同时显示机载视角；策略日志与隐藏评测日志分开。无示教 Direct 的成功必须来自实际物理接触，不能用绑定物块或改状态的演示。

本机 SIMPLE 环境包含 Isaac Sim 4.5；上游 RoboDojo 使用 5.1。迁移时优先复用本地 SIMPLE 的命名 q29 bridge，补齐任务资产/reset/摄像头和 single-writer backend，然后先做 HOLD 与命名关节语义检查。关节顺序以 model_38000 随附文档为准，不能凭 Isaac 的习惯推断成 BFS 顺序。当前尚未在 Isaac 跑出本任务结果。
