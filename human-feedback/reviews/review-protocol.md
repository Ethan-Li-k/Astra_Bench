# 人工纠错审查协议

本工具只接收公开判断，未启动物理复现，也未训练 GPT 权重。H001 的用户已知失败；不能将此例称为盲测。原话是 annotation，归纳是独立 rule，初始一律 `human_proposed`；认可率不是物理成功率。

1. **公共证据对齐**：双方使用同一 case/source 哈希、时刻、原始左右目、命名机器人状态和公开动作。记录先前是否看过 agent 摘要、后果、后续帧及追加视角。先收初判，主动展开冻结的事实/假设/缺失信息/预期现象后另存补充。额外视角必须同时提供给两方并另记信息条件。H001 缺完整历史 skill/控制器/工具合同版本与初态 checkpoint；不能靠当前文件补称当时版本。
2. **冻结原失败并复现**：agent 收集旧控制版本、skill、初态/seed、完整物理 checkpoint、必要历史及动作时序。用旧控制真实重新执行并记录差异；录像回放仅核对历史，不是新成功。无法恢复同初态就记录 `reproduction_unavailable` 或 `approximate`，不得冒称已复现。host 审计可独立核实结果，隐藏对象/contact/reward/oracle 不进入用户或 actor 包。
3. **一次改一个判断规则**：把用户原话与 agent 提炼分开，明确触发条件、预期现象、反例、未观测项和版本；有歧义只作一条区分性追问。新独立重置物理回合使用 `human_feedback_used=true`、`human_demonstration_used=false`、`evaluation_stratum=human_feedback_assisted`；控制/初态/评估尽量保持，仅改已指定判断门槛。具体合法动作和安全边界由 agent 实施，本 UI 无动作接口。
4. **仍失败则问一个能区分原因的问题**：给同结构前后证据及互斥预测，区分观测不足、几何/空间判断、规划门槛、跟踪/可达性、控制接口和结果判据错误。不得把所有失败归为模型推理或反复要求用户设计轨迹；失败录像与历史保留。
5. **新 seed / 场景验证**：同初态改善后，再检查不同初态、布局、抓法及负迁移反例；预测、完成条件、真实重置与审计证据缺一不能晋升。当前 H001 原失败动力学复现、修正规则物理回合及迁移均未由本工具执行。
6. **按机制晋升**：提交短规则候选（when_to_use / when_NOT_to_use、证据、反例、旧/新版本、回滚条件）；SIMPLE supervisor 是公共 skill 唯一发布者，遵守现有 831 words / 6250 chars 上限。自主 Direct 与 human_feedback_assisted 分层报告成功/失败、信息条件、独立重置及求助次数。学习载体是外部 skill/历史/反例，不称权重训练。

H001 当前三条桌面转录均保留原话，第三条只修正之前 agent 对高度门槛的过度泛化。抓法相关条件不能静默统一为“掌心与苹果等高”，也不能把“同心圆”擅自变成固定半径或隐藏世界坐标。详见 `H001-rule-001.json`，状态仍为 `human_proposed`。

研究借鉴（参考仓库不构成本项目执行授权）：

- [GPT-as-Policy gpt-only 短 skill、NOTES/history、原始观测与结果边界](../../ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md)：复用简短规则、失败历史和公开状态，不复制其动作接口。
- [RoboRSI diagnose_atomic_failure A–D](../../ref/RoboRSI/roborsi/embodied/skills/_lib/human_review/diagnose_atomic_failure/SKILL.md)：借鉴判据矛盾、规则执行、运动/IK、底层几何的分层排查；每层要有独立证据，不照搬其强制动作或判断真值访问。
- [expert_trajectory_reflection](../../ref/RoboRSI/roborsi/embodied/skills/_lib/human_review/expert_trajectory_reflection/SKILL.md)：其 contact_points_pose / 专家 oracle 读取不适用于本任务，未复制、未调用。

## 最新覆盖：视频反馈与求助门槛

当前首页为只读视频/进展页，H001和F001不再展示待答问题，网页提交接口关闭；这覆盖上文旧流程中直接追问的触发时机。只有同一未解决机制的至少3次可比、真实、独立重置探索完成并经过审查，且已有自诊断仍不能解决，才选代表性失败交用户分析。必须列明真实reset/episode来源、控制与初态可比性、各次假设/区别/结果，去除同一回合、固定旧动作复现、回放和接口错误；不能按文件数或视频数凑3次。证据不足保持关闭，不自动放行。本页没有达标自动开表单的逻辑。

H001状态更新来源为 `reproductions/H001/status.json`：旧动作基线已由协作复现分支在新动力学运行中复现失败，完成65个原动作，闭合/抬腕片段来自该运行。此前“尚未复现”的描述仅代表先前交付时点，现被此状态取代。没有宣称完整隐藏状态等价、根因已确认或修正规则成功；本UI没有执行新的仿真。H001三条用户原话继续绑定冻结case；F001已有原话保留于其所属协作分支，不重复询问或重新归为无反馈。

视频信息条件：完整物理录像、连续片段和精选帧序列必须分别标注。H001片段是从新物理基线的合成录像提取完整头部左目画幅；提取本身不是新物理回合。F001基线左侧是外部track诊断视角，右侧为head_cam；完整合成画面含额外信息，不能称与原策略同信息。`actor-observations.mp4`是精选静止帧序列，不是连续录像；本页使用实际连续基线录像。HTTP仅暴露三个明确授权的视频路径与筛选后的公开进展，不暴露host审计文件、对象真值或隐藏接触状态。

共同控制、locomotion和机制经验路由沿用既有角色/skill报告，不新建代理框架。公共skill仍由SIMPLE supervisor唯一发布；复现、人工辅助修正与自主Direct结果分层，不将失败基线算成功。协作分支已记API费用3.39元，本UI不修改账本。
