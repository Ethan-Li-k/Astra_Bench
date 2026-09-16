# Account 2：角色分工、skill 学习与 IKEA 门槛

2026-09-16，独立本地代码评审；固定 Astra/xhigh，未调用模型实验或付费 API，未训练参数，未启动仿真。SIMPLE 推门真实成功仍为 **0**；locomotion 为 **未验证**。本报告是建议，不是跨任务收益已证实的实验结论。具体源文件版本见 [source-manifest.json](../artifacts/R020/source-manifest.json)。

## 判断

采用**同一冻结 Astra 的角色职责 + 版本化短 skill/外部经验 + 确定性 router**。先保留既有 supervisor 和每环境唯一 Engineer；Planner、Reviewer 是按事件执行的工作阶段，无需新建四个常驻代理。角色提示、上下文和权限不同不等于训练四套模型，也不保证统计独立；Reviewer 需要从原始证据重新判断，不能只读 Engineer 摘要。

实际训练四套模型要另有可训练执行器/模型、四份任务数据与损失、优化过程、checkpoint 和独立评测；当前这些角色模块调用既有模型并保存文件，不能作为参数训练证据。参考库另有 posttrain 概念，不代表角色本身已训练，更不代表 RSI 获得该能力。当前没有已确认的训练服务/预算，先不建立四套训练管线。[Engineer](RoboRSI/roborsi/agents/engineer.py#L131)、[Planner](RoboRSI/roborsi/agents/planner.py#L497)、[Reviewer](RoboRSI/roborsi/agents/reviewer.py#L683)、[long_horizon 示例](RoboRSI/roborsi/embodied/skills/long_horizon/clean_table/SKILL.md)。

skill router 已足够：它选择可调用工具/经验；这里没有可训练专家子网络或逐 token 门控，不能称为神经网络 MoE。更多角色也不能修复脚目标不能导致步进的控制缺口。只有在多任务、版本匹配的数据证明“选择错误”成为主要瓶颈后，再比较小型 router/失败分类器；执行器蒸馏/微调需另立实验，不预先要求 MoE。

## 最小执行设计

- **Manager / 既有 supervisor**：新用户指令、任务切换、资源变化、晋升请求时触发；管理重置身份、单写入者、预算、待办与门槛。验收是无重叠所有者、来源可查的 ledger、晋升/拒绝及回滚版本。一般轮询与计数用脚本，不额外问模型。
- **Planner**：新任务机制、前置条件改变，或一次有证据的重大失败时触发；输出短子目标、可观察验收、风险、可调用技能 ID 和本轮唯一待检验变化。两次同模式失败是诊断触发器，不是“必为工具 bug”的证明。验收是不杜撰工具、不改任务、不复制物体坐标、不把未验证步进当依赖已满足。
- **Engineer**：每环境唯一动作写入者，闭环继续用完整 Astra 推理；每次实测后核验执行，不因慢推理截断、重发。验收包含 observation/action ACK 链、真实 backend、reset ID、完整回合/录像、skill 修订与失败记录。
- **Reviewer**：完整回合结束、接口/控制器改变、申请共享晋升时触发；先跑零模型 host 校验，再在证据歧义/故障归因/迁移提案时做独立 Astra 审查。验收逐项区分物理结果、观察事实、原因假设和下一步测试；一条提案有证据引用、反证和回归结果。不是每个 chunk 串行调用四角色。

所有角色只保存公开理由/决策，不导出私有思维链。host 真值仅供审计，回传 actor 的经验要剥离隐藏物体状态/奖励/oracle。预算、模型推理等待、动作到位超时、物理回合预算分别记录；暂停物理的诊断不称实时闭环。

## 相似性与负迁移

采用四层索引：共同控制接口（坐标、单位、时序、腕/手指校准）；locomotion（站稳/移重/步进/接近/绕障，逐项验证，当前步行未掌握）；交互机制（抓放、容器、接触关节物）；任务实例（可达侧、推/拉、铰链、把手/锁舌、初态）。不能因两个任务都叫 door 就共享动作配方。RoboDojo X5 的 link6、wxyz、0/1 夹爪语义可借鉴成“显式 contract”的写法，不能当作 G1/Dex3 的数值校准。[EEF contract](../GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md)、[门技能排除条件](RoboRSI/roborsi/embodied/skills/base/open_hinged_door/libero/SKILL.md)。

router 在回合开始和证据否定前置条件时重选：先硬过滤 embodiment/backend、control contract、版本、机制、前置条件及 `when_NOT_to_use`；未知条件进入待验证集合。再按同机制、同接口的**独立成功数/总尝试数和相关失败**排序，少量候选附适配理由。缓存键包含任务说明、能力条件、skill+依赖哈希、registry 版本、观测类别和经验版本；不能只看名称/总成功数。回合中 pin 住技能版本，更新下回合生效。

每条经验保留 `id,parent,scope,status,contract_hash,skill_hash,controller_hash,task/mechanism,preconditions,when_NOT_to_use,source_episode/reset_ids,evidence_hashes,failures,review`。状态至少区分 hypothesis、observed、locally_validated、shared_validated、retired；管理同意一条线索不会自动把它变成物理事实。失败与旧版本保留，短 wiki 只存索引和摘要，主 skill 总长仍 ≤831 words / 6250 characters（现有额外约束5357非空白也保留）。[短 skill](../GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md)、[teacher_context](../GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/teacher_context.md)、[现有 RSI memory](../rsi/skill_learning.py#L49)。

晋升流程：任务本地提案 → 隔离副本验证 → 同任务复现 → 另一匹配机制任务验证 + 原抓取回归 → 单一 Manager 原子发布带依赖哈希的新版本。不能验证的经验留本地/experimental；遇反证立即降级并回滚引用，原证据不删。既有 [skill_transfer](../rsi/skill_transfer.py) 已具备共享核心+任务分支和来源 manifest，可增量扩展，无需替换当前 runner。

## 对参考实现的独立核查

1. `Engineer.execute` 只在 robotwin 活跃技能 **>50** 时调用 selector，默认 top15；在这个调用点是执行前一次、`recent_results=[]`，不是文档所说的逐步动态路由。selector 缓存还缺 scene/index 等输入。少工具场景无需增加 selector 模型调用。[Engineer](RoboRSI/roborsi/agents/engineer.py#L150)、[selector](RoboRSI/roborsi/agents/skill_selector.py#L61)。
2. history 给成功回合中用过的每种技能记一次；这是关联，非该技能成功的因果证据。版本以 `git log` 最后提交为准，未提交编辑/依赖变化不失效，且没有失败分母、episode/reset 去重字段；RSI 应采用内容+依赖哈希和独立回合计数。[history](RoboRSI/roborsi/agents/skill_history.py#L33)、[调用点](RoboRSI/roborsi/agents/engineer.py#L243)。
3. wiki 将失败观察和原因假设分离、保留 archive、将 seed plan 晋升排队，值得采用。但 approved lead 仍需标注证据等级；`resolve_policy_proposal` 做安全检查后写入，并未自身执行仿真 gate，不应把说明文档视作所有调用路径强制验证的保证。[task wiki](RoboRSI/roborsi/agents/task_wiki.py#L267)、[policy apply](RoboRSI/roborsi/agents/task_wiki.py#L546)。
4. validator 的 capability 与功能门槛分离合理，但 `_stage_and_gate` 会临时覆盖共享 skill 后还原，独立环境并行时会产生读写竞态。只支持部分 robotwin base harness，其他类别拒绝自动功能通过。Reviewer 的 auto 路径也会 `_auto_apply --skip-harness`，并非所有路径都等待 Manager；不直接复刻这套治理。[validator](RoboRSI/roborsi/agents/validator.py#L63)、[Reviewer](RoboRSI/roborsi/agents/reviewer.py#L733)。
5. Reviewer 原子路径会去除 GT 字段，long-horizon 路径会读 GT，而且旧提示还包含 `describe_scene_actors` 等与 pure-vision 冲突的建议。借鉴证据优先级，不照搬其工具权限/模板。Manager/Engineer 的“删除诊断”要求不适用于本项目，诊断全部保留。[两条审查路径](RoboRSI/roborsi/agents/reviewer.py#L763)、[Manager](RoboRSI/roborsi/agents/manager/MANAGER.md#L160)。

验证设计：等控制接口可用且出现 SIMPLE 真实成功后，固定控制器、task spec、初态/seed 集合、经验版本与总预算，成对比较单 agent+本地 skill、共享核心+任务分支、再加事件 Reviewer。留出独立 reset/任务实例，比较 host 成功率（分母保留）、重复无效动作、迁移后退化、调用数和完整等待时间；不得混合 PD/初态后宣称角色收益。当前不运行这些实验。

## 本次可执行交付与边界

[ikea_gate.py](../tools/coordination/ikea_gate.py) 提供 check / wait / enroll，零模型调用。只接收既有 supervisor 审核真实启动/重置来源后的 receipt，再核验哈希、完整 turn、接触、开角≥30°、连续≥1秒、站立、全程连续 ticks、动作数及完整录像；去重 episode/reset/进程/trace/video。缺 provenance 拒绝，不能给旧回合补造身份。生产目录固定，合成测试不会登记；信任边界是可信 host 的来源证明，本地文件哈希本身不能鉴别伪造的物理录制。

当前 0/3；即使达到门槛，API 来源、正数费用上限、币种和用户答复记录缺一仍待机。全部满足时也仅登记 `eligible_registered_only`。实际付费调用还需分支执行器落实预算扣减/停止，本入口没有模型/仿真启动功能。当前未探索 IKEA、未改 USD。说明见 [coordination README](../tools/coordination/README.md)。

用户要求已通过第二账号正规 `queue` 排入指定 supervisor thread，回执不代表已读；是否出现新公开日志明确 ACK，以 [coordination-status.json](../artifacts/R020/coordination-status.json) 为准。既有通道可用，因此不建立并发 resume。门槛与 ACK 等待由独立 tmux 零模型观察器承接，不让主账号轮询。
