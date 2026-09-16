# 第二候选：任务审计决定成功检索资格，尚未合并

本轮只改 `memory-priority/` 中的候选。线上SIMPLE第二账号supervisor `01a0a867-d7aa-71f2-8547-e264d6d09ede` 仍是唯一发布者；API工程师写域、在途物理和推理不动。第一轮完整交付保留。原始代码/案例hash见 `original-manifest.json`，成品hash与漂移检查见 `manifest.json`。

## 复现与修复范围

真实案例：`artifacts/R019/boxplace-campaign/episode-0001` 的 `result.json` 和 memory row均为native success，而 `success_review.json` 的 `audited_task_success=false`。其公开lesson已明确没有完成lift/transport/release。旧SkillMemory仍只按native success保留最早记录。复现使用该原始公共row加**五条明确标为合成的后续未完成记录**；旧选择 `[1,4,5,6]`，被否决的1挤掉较新的3。不是声称原campaign已有六个回合。[复现证据](evidence/reproduction.json)。

修改五个文件，不新建成功账本、审计写者、model selector或角色进程：

1. `rsi/skill_learning.py`：加入host-only `success_review`回调。`read()`只在原生结果为success、现有审计通过、原回合完整且当前completion contract匹配时保留最早成功；默认最近4条和显式版本查询仍可返回失败/反例。返回时附3个固定字段：`task_audit_status`、`completion_contract_matches`、`success_priority_eligible`。原始经验不改。
2. `tools/audit_simple_campaigns.py`：复用现有 `episode_status()` 的完整turn、真实动作、skill更新、无error与审计成功判断；新增审计三态及 `memory_success_review()`的最小投影。completion contract优先读新result字段，兼容旧scene字段及原有door/native默认ID。没有把result.success重新定义成任务成功。
3. `tools/learn_simple_task.py`：在现有 `memory=SkillMemory(...)` 行传入 `memory_success_review(root, specification.completion_contract.id或native_simple_criterion)`。读取规格发生在该构造之前，`--verified-placement`仍先设置原来的PLACEMENT_CONTRACT。
4. `tools/learn_door_skill.py`：同一构造点传入当前合同ID，默认复用现有 `door-push-contact30deg-dwell1s-standing`。
5. `tools/learn_grasp_skill.py`：仅更新experience_read工具描述，说明审计及合同条件。独立候选不改任何执行/终止逻辑。

## 审计晚于skill_update的实际接续路径

```
LearningHost.skill_update -> 原memory/experience.jsonl与versions（保持原始outcome）
现有supervisor完成审查 -> 原episode/success_review.json
下一次experience_read -> SkillMemory.read -> 已接线的host回调
  -> 同一个episode_status -> 三态/合同/完整性标签 -> 选取公共经验
```

写入仍由**现有审计owner**完成。例如本轮快照 `tools/review_completed_door_episode.py:82–84` 已在审计通过后写 `ep/'success_review.json'`；该文件中有 `audited_task_success`。抓盒/放盒由现有supervisor写同名审查文件。**无需新invoke/set-label步骤，也无需要同步的第二份状态**：回调每次read重新读取现有文件，不跨调用缓存。接线的两个真实caller已有补丁，不是未使用的可选字段。

同一实例测试覆盖：先skill_update、后读为unknown；owner发布通过审查，下一read能置顶；随后fixture中改为否决，下一read立刻不置顶且journal/versions/skill字节不变。fixture覆盖撤回语义，不授权线上静默覆盖历史审计；真实审计修订仍遵守现有owner的保留/复核流程。审查文件正在写入而JSON暂不完整时，返回unknown且不保留旧批准；下次read重新读取。

## 具体行为与边界

- 审计否决：`rejected`、不可作为成功优先项；可作近期反例或显式版本读取，原始 `native_outcome=success`不改写。
- 历史未审计/缺审计/无provider：`unknown`、不可成功置顶。默认构造器不接审计的旧Direct caller也保守如此；这只影响检索资格，不倒扣桌面10次物理成绩。没有把旧桌面审计汇总冒认成这里的SIMPLE审查文件。
- 审计通过：仍需已完成、有动作、完整turn、skill更新、无error、原生success及同合同才可置顶。只有审计bool而回合未完成或有执行故障，不置顶。
- 合同变化：可以显示历史审计passed，但 `completion_contract_matches=false`且不置顶。这里只比较既有**completion contract ID**，不是新建通用controller/router能力证明。同一ID须保持定义稳定；改阈值/语义应版本化。控制器/观察合同/任务实例适配仍由现有来源选择与独立评审负责。
- 人工反馈：不从host标签推断或补填actor row的人类反馈字段。已有true/false原样保留；旧缺失仍缺失，不重标自主。现有result/human_feedback_review的分层统计不变。

host审查可读接触/物体/奖励，但回调只返回三项标量，SkillMemory再按固定字段提取，**不展开audit字典、原因、路径或隐藏值**。恶意/额外callback载荷、原始审计秘密标记均有不泄露测试。公开经验自身的原路径和lesson原样保留；本补丁不把审计解释改写为视觉事实。显式读取旧journal依然看到原始历史，而最新检索资格由experience_read提供；不假称已清洗全部历史文字。

## 发布顺序

两种成品择一，不能重复叠加：

- 只集成本项：对照 `baseline/` hash，应用 [memory-priority.patch](memory-priority.patch)。它不引入长度门槛，不更改现有技能正文；18项针对测试通过。
- 同时集成第一项：先按第一轮要求压缩全部受影响任务的入口、保留原版本，再应用 [combined-compatible.patch](combined-compatible.patch)。它已经整合两个构造函数改动，保留原runtime文本与completion_contract回执字段；18项检索测试与8项原长度测试通过。短入口副本与第一轮一致，不新增技能规则。

初次尝试把两个独立patch直接叠加时，构造函数hunk冲突；日志、reject和失败测试均保留在evidence。已手工保留两个属性并形成组合补丁，最终对原始快照dry-run通过。**不要用初次失败的叠加方式发布。** 若publisher已经合入第一项或live hash变化，只逐hunk重基并重跑检查；不整文件覆盖。

离线复核命令（在评审根目录执行，仅写本子目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 python memory-priority/tests/test_memory_priority.py
PYTHONDONTWRITEBYTECODE=1 MEMORY_PRIORITY_TREE=combined python memory-priority/tests/test_memory_priority.py
PYTHONDONTWRITEBYTECODE=1 python memory-priority/tests/test_prior_length.py
patch --dry-run -p1 -d memory-priority/baseline < memory-priority/combined-compatible.patch
```

`LearningHost.dispatch/next_call/__init__`、SIMPLE/door main除memory构造外的AST与基线一致，覆盖早停、执行故障、staged-placement、human-feedback和任务设置代码保持；这不是新增物理测试。没有运行仿真、API或模型，未创建环境。最终漂移检查只检查本次相关快照，不扫描仓库。

## 交给SIMPLE测评者的紧凑验收计划

先做离线旧/新选择A/B：同一真实公共record与同一合成后续记录，旧函数错误置顶1，新函数得到最近3–6；再使用相同合同的已通过审计成功验证保留能力。审计否决/未知/不完整/改合同都不得进入成功优先集合，原文件hash不变，host隐藏内容不在actor包。此项是发布硬门槛。

物理小样本由SIMPLE单一执行owner另行安排，不故意把已知审计否决项重新作为线上成功范例。安全A为**同一标签投影但关闭成功置顶、仅最近4条**，B为本候选；它比较成功检索优先级的效用，**不冒称原bug的物理因果复现**。固定控制器/checkpoint、UMI-4界面、初始reset/seed与资产修订、completion contract、相机、技能/公开memory快照、人工反馈tier、物理和模型预算；配对3个新reset，A/B顺序交错。两臂共用同一短入口或同一现有入口，避免同时改变长度、placement准则或控制器。

每对记录：实际selected source IDs、适配/排除理由、完整视频、独立host task成功与终态保持、动作数/重复无效动作、工具调用和完整等待时间、终止分类；不混入诊断回放。硬门槛仍是零否决/未知成功置顶、零host泄露、零新增提前结束/执行异常。若B在A成功的配对上丢失同任务终态，或反复无效动作增多，暂不晋升，保留视频复核；3对只作回归筛查，不能建立泛化/统计显著性。调用成本需另外记录，因为当前复用episode_status会读已有回执文件；没有增加模型调用。

选用的公共经验与必须重查的条件：

- **放盒0001反例**：来自该episode公开lesson/history与动作022；已有公开文字明确未执行lift/transport/release。不选其为成功配方。重查当前rim/手部净空、包络、搬运释放过程，以及当前是否是staged-placement变体；host否决只作标签。
- **同任务已审计成功**：通过现有callback在本campaign按最早合格版本选择，不硬编码某次动作。推门可用第一轮已核验的0011公开stall→继续卸载/调整/推门经验；重查asset/frame修订、站位与当前视觉。其数字坐标不跨任务复制。
- **locomotion→manipulation→locomotion**：地面分支的接近经验只作为机制候选；本补丁不自动把它接到SIMPLE抓放。移动/支撑与手部几何经验分开选择，重查控制合同、静止可达、夹持保持和放置后移动条件；无兼容公共证据时记录“本轮不迁移”，不强拼轨迹。

新回合由现有 `experience_select`记录具体原子来源ID、选用理由、前置条件、预期可见结果与不复用部分；没有新增角色调用。候选未部署、无物理收益结论。
