# 第二项有界修复完成：候选未合并

已用真实放盒0001的公共经验与现有审计否决回执复现：旧实现会把native success作为优先项，即使任务审计已否决。为展示“挤掉近期记录”的行为，复现加入了五条明确标为合成的后续记录，没有新增物理尝试。[复现](evidence/reproduction.json)。

候选复用现有 `success_review.json → episode_status`，由SIMPLE和推门runner的真实SkillMemory构造点接入。每次检索重新读取审计，所以skill_update之后发布的审计也能立即影响下一read，**不重写原经验、失败、版本或人类反馈标记**。否决/未知/回合不完整/执行出错/合同不匹配均不能成为成功优先项；反例仍可按近期或版本检索。

actor仅得到审计三态、合同匹配与资格标量，隐藏审计内容、原因和路径不进入输出；普通历史native标签原样保留，不改称审计成功。默认没有审计provider的旧caller保守地不置顶未核验成功，物理成绩账本不变。

- **18项检索回归通过**，独立补丁及组合版本各通过；覆盖真实反例、审计后补/撤回、成功保留、失败/未完成、合同变化与未知、人类反馈不重标及隐藏载荷隔离。[测试日志](evidence/regression-final.log)。
- 与第一项组合后，**原8项长度回归通过**；最终两份补丁对快照dry-run通过。首次直接叠加的构造函数冲突与失败日志保留，已提供解决后的组合补丁，不能直接重复叠加旧补丁。
- 原早停、执行故障、staged-placement和反馈代码保持不变，AST核对通过。第一轮候选文件hash保持一致。没有API、额外模型调用、仿真、新环境或在线文件修改。

发布者可只应用[本项补丁](memory-priority.patch)，或在各任务短入口已准备好后应用[组合补丁](combined-compatible.patch)，二者择一。代码基线hash、最终漂移检查与成品hash见 [manifest.json](manifest.json)。调用点、审计owner的原写入路径及固定控制器/reset/合同的A/B验收计划见 [INTEGRATION.md](INTEGRATION.md)。

第一轮认可来自父任务转述的协调者消息，已在新回执明确标注来源和原话，不冒称直接读取或已集成。本轮通过原SIMPLE inbox追加一次交接；只算queued，未获本候选ACK、未部署。详见 [coordination-receipt.json](coordination-receipt.json)。

剩余工作：唯一在线发布者核对当前hash并集成，SIMPLE测评者按计划提供独立回合、视频与退化审查。completion contract ID匹配不代表全部控制/任务实例兼容；旧记忆文字与显式归档读取未被改写。**当前仅证明离线检索行为正确，不声称物理成功率提高。**
