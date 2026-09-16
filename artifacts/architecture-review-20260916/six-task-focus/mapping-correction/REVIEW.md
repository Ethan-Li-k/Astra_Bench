# 六项精确映射修正 v2（候选未部署）

本版取代 v1 的暂定映射、任务安排及集成建议。旧版完整保存于 [version-v1](version-v1)，原目录未改；[归档回执](archive-receipt.json)记录逐文件 SHA256。旧成功、失败、暂停、视频及工程记录仍是原事实，本轮没有新增物理成绩。

对 [root review](snapshots/root-candidate-review.json) 四项逐项回应：

1. **Grasp** 已明确 `simple/G1WholebodyTabletopGraspMP-v0`，删除“待用户澄清”和错误的非 Wholebody 名称。待办是 publisher 的原生资产/手型/控制兼容验证，不是重新向用户选任务。[delta](candidate/deltas/grasp.md)
2. **Mobile P&P** 改为 `simple/G1WholebodyLocomotionPickBetweenTablesTeleop-v0`；MobileCheezit 仅历史迁移来源，不再建议续测抵分。终态是目标容器内放置/释放，不是泛指到第二桌。[delta](candidate/deltas/mobile.md)
3. **BendPick** 绑定 `simple/G1WholebodyBendPickMP-v0`；Teleop episode0006 与 SimToReal 反例仅在条件匹配时迁移方法，不能继承 MP 成绩或旧8cm准则。[delta](candidate/deltas/bendpick.md)
4. **Handover** 绑定 `simple/G1WholebodyHandoverTeleop-v0`；明确右手承载、左手接管、右手退出后的独立留握、容器放置与释放。放置必需，不再限定于可选 PlaceBack 变体。[delta](candidate/deltas/handover.md)

其余两个 delta 也显式绑定 `simple/G1WholebodyXMovePickTeleop-v0`、`simple/G1WholebodyXMoveBendPickTeleop-v0`。已验证 XMovePick skill 优先保留；新模板不是强制替换。六项来自原 README:567，原文件及四项原生任务源码的 SHA 与 root 证据一致，见 [来源](source-hashes.json)。

原生判据与完整任务分开。BendPickMP 默认抬升9cm，TabletopGraspMP 默认1.8cm，都不原生证明留握；HandoverTeleop 容器接触累计并不检查真实右到左承载；BetweenTables 的接触顺序存在 `or`/`and` 优先级差异。本轮保留其原生语义，不修任务源码。完整承载/移交/放置另列于 [host-contracts.json](host-contracts.json)；该文件及 native 源码禁止进入 actor 包。精确源码行、公式和局限见 [root 原生审查](snapshots/canonical-native-root-review.json)。

短共同合同只把终态“修订后加载”收窄为“提交建议，仅学习阶段可加载”。最新 [SIX-TASK-FIVE-STABLE-V1](snapshots/ref/USER_UPDATE_20260916_SIX_TASK_FOCUS.md)要求固定候选五连胜后独立十回合冻结测评，覆盖 v1“每类一次/已达标不重开”。本轮没有实现计数器或冻结加载隔离。[当前 caller:162](snapshots/tools/learn_grasp_skill.py:162)仍直接 `memory.update`；仅修改文字不能证明后续回合不读新经验。publisher 须先隔离加载和评价输出，未通过前不得声称此候选可用于冻结测评。

沿用已完成审查：GPT-as-Policy 第一参考，复用短入口、按需公开经验、实测反馈与 ACK 后复核的结构；[此前引用的 EEF 合同:9](version-v1/snapshots/ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md:9)。RoboRSI 只作阶段和适用前提的次要参考，见 [原架构审查](../../REVIEW.md)。未重做参考研究，未移植机器人参数或对象特权信息。

静态验证涵盖六项原文映射、共同入口+完整单 delta+当前 immutable/续接静态提示总长、超长拒绝、技能格式和源漂移。它不证明 MP 可运行、冻结隔离已实现或物理成功率提升。当前任务数据、观测和工具 schema 与静态入口计数边界分开，沿用现行 caller 合同，不把任意附件称为已过总长检查。
