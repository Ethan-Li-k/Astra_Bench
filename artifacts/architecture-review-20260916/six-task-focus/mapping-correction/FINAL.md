# 六任务映射 v2：静态修正完成，候选未部署

已逐项修正 root 的四项要求：Grasp 明确 WholebodyTabletopGraspMP；BendPick 绑定 BendPickMP；Mobile 绑定 LocomotionPickBetweenTablesTeleop；Handover 明确右到左独立承载后必须容器放置。全部六个精确 ID 见 [任务安排](TASK-PLAN.md)，旧变体只作有条件的历史来源。MP 待 publisher 兼容验证，不再待用户澄清。

v1 的134个候选/检查/报告/证据文件已按字节归档，旧目录未改；见 [归档回执](archive-receipt.json)。[逐项回应](root-review-response.json)、[候选差异](candidate.patch)和 [host 合同](host-contracts.json)齐备。原生分数与真实留握/转手/搬运/放置审计分开，host 资料不进入 actor。

六个完整“共同skill + 一个delta + 当前runtime/续接静态文本”检查通过，各维最大742 words /5638 chars /4896非空白，低于831/6250/5357；技能格式、README映射、原生源码SHA和对v1的patch dry-run通过，无截断。[检查回执](checks/summary.json)、[最终源漂移](checks/source-drift.json)。本轮只做静态修正，未动在线代码、技能、进程或机器人，未调用模型实验/API。

[集成说明](INTEGRATION.md)明确唯一SIMPLE publisher在自然边界逐段审核，保留现有有效XMovePick skill，验证实际最终入口再选择delta。最新“五连胜后独立十回合冻结测评”已反映；MP控制适配及冻结加载/检索隔离仍由publisher实施验证，本轮没有把文字约束当已生效代码。

已向唯一SIMPLE publisher发送一次辅助队列交付，queue ID `01a0aa52-47f2-7811-a2ea-a3f9f26ff5b4`，见 [delivery-receipt.json](delivery-receipt.json)。尚无本版ACK或集成证据；排队不等于物理收益。账号2，openai/gpt-6-astra/xhigh，启动证据见 [result.json](result.json)。此有限修正交付后结束，不等待全部机器人目标或集成。
