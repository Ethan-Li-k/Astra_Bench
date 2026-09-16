# NT-20260916-v1：未合并的连续性候选

当前问题：网络错误通知、网络终态和主机重启被混同，会造成误恢复或误报。总目标：保留同一有效 episode 的进展，且不重复未知动作/请求。不可重犯的错误：不靠取消/重发长推理解决沉默，不跨越授权边界。

## 准确的适用范围

候选仅修改 [CodexPolicyAdapter](candidate/rsi/codex_app_server.py)，不修改在线源。原来的 `next_message(None)` 已无推理时间限额；SIMPLE caller `while not host.skill_updated` 也已有普通 turn 连续执行。API `HTTPSConnection(timeout=None)` 同样已修复，不重做。

本次先在原文件复现，再处理两个相邻边界：

- `start_turn` 的 RPC ACK 原来仍使用 `timeout=900`。候选使用 None，并在发出前设置不确定提交锁；ACK 异常/缺失后，同一 adapter 拒绝第二次提交。这不是已证实的近期 900 秒中断，也不是跨进程恢复功能。启动/初始化 RPC 的连接期限保持原样，不属于任务推理期限。
- 匹配 thread/turn 的 `turn/completed(status=failed)`，且错误明确属于网络断线，且本 episode 尚未终止、后端无待执行动作、有上次网络恢复以来的新物理 action，才在原 `run_turn` 内创建同 thread 后继 turn。原 host/backend/reset 不变，先保存完整失败终态，再交给 actor 当前公开 next_call，要求核对已有公开回执、NOTES 和新观测。代码不发送旧动作或旧 turn 输入。

只有本地 reply 写出，不能称服务端已经收到 ACK；候选提示明确要求重新核对。`actions` 仅作 host 控制进展门槛，不向 actor 传隐藏审计。恢复消息不含原始 error、对象/contact/evaluator 值。tool error、EOF、未知提交/回复、额度/授权/安全错误、incomplete/interrupted、后端 active 或物理终止均不进入重试。HTTP401/402/403/429 明确排除。

无新物理进展的连续网络终态记录 `no_new_physical_progress` 并交还现有错误路径诊断，**不无限创建空 turn**。这时旧 turn 已经明确失败结束，不是截断在途推理。当前 caller 最终仍会 close；本候选没有提供持久 checkpoint，也不声称该分支可无缝续接。门15只有 error 通知而没有 terminal，故本候选对这段通知只等待，绝不自动重启。重启前的状态丢失不在可恢复范围。

## 发布者操作与确切接入点

公共 publisher 仍是 SIMPLE 辅助 supervisor `01a0a867-d7aa-71f2-8547-e264d6d09ede`。等其确认的自然边界，归档现有版本并检查 [snapshot-manifest.json](snapshot-manifest.json) 和 [漂移检查](evidence/snapshot-drift.json)。不得复制整份旧 snapshot 覆盖并发修改。

1. 先完成原长度/审计优先级候选的任务入口压缩和审计接线，使用 `../memory-priority/combined-compatible.patch`；不要重复叠加首轮长度补丁。
2. 再逐 hunk 审查 `continuity.patch`。它只改 `rsi/codex_app_server.py`，与前一组合补丁的五个文件不重叠。[compatibility.json](evidence/compatibility.json) 已在当前源的本目录副本上按此顺序执行零 fuzz dry-run、应用及语法解析；在线文件未改。
3. 真实调用点是 `tools/learn_grasp_skill.py:304` 构造 adapter、`:308` 调用 run_turn。候选在这里直接被使用，不需新增未接线 callback；`:318` 清理仍只在 run_turn 返回/抛错之后执行。[调用链测试](tests/test_caller_integration.py) 从实际快照 AST 提取整个 run_episode，用假 transport/backend 验证网络恢复期间 host 未 close、同线程两次 turn、每个动作仅一次，最后才清理。没有物理执行。
4. `skills/{simple,ground,ikea}/SKILL.md` 是**含公共短合同的完整候选入口**，不是再拼到既有长 core 后面的追加段。SIMPLE publisher 将所需差异融入现有任务装配规则，重新检查实际最终入口+runtime；保留任务目标/阈值于 workspace 的 completion_contract，不删除原经验版本。不要三份共同内容再次相加。
5. `skills/public-sources.json` 是评审交接的公开来源映射，不是新增运行时注册表。用现有 `skill_sources`/transfer_sources/experience_select 给所选来源登记原 ID 或明确别名，并限制为这些公共文件；不复制 source-manifest、host 审计、隐藏 scene 状态到 actor。若 source ID 不兼容，先修映射，不能假装已选中。

实际 developer 指令组合：SIMPLE 673 words / 5201 chars / 4520 非空白；ground 492 / 3714 / 3215。额外计入新恢复静态提示后 SIMPLE 为724 / 5527 / 4795，仍合格。动态 next_call 是 episode 数据，发布者应核对最终实际装配，不以截断满足上限。IKEA 的679 / 5146 / 4459 仅对拟复用 LearningHost runtime 成立，**尚无实际 IKEA actor runtime**；正式适配前不可宣称通过运行入口验收。三份技能结构校验均通过。

API actor 是独立 Responses 调用链，本补丁不能直接套用。其 owner 保留120请求/180物理秒/共享10000元和原费用预留规则；本审查不读账本、不查询额度、不发请求。第55次请求结果未知，不重发。恢复 owner 已变为 `01a0a982-cec5-71c0-b771-091c31df61f2`，详见其 RECOVERY；本次仅获准向 delivery.json 中旧辅助入口排队，要求既有协作链转交，不能唤醒旧线程或自行增加收件人。新物理回合需 owner 独立确认状态/授权，不能沿用旧单 episode 凭据。

IKEA owner `01a0a96b-06cc-7150-8c73-7b0897936b52` 先声明实际 scene/controller/mechanism/runtime 合同。SIMPLE fixed-frame push-open ≠ 原场景门/把手解锁；静态/接触诊断不是 actor 成功。已有 API/IKEA 扩展任务/安装/预算请求已阅读并保留归属，本审查不执行。

## 原 owner 验收，不在本轮运行

先重跑本目录离线测试、原 adapter tests、技能结构/实际装配长度；验证未知请求、willRetry通知、EOF、额度/安全、active backend 都不会造成重发。再由 SIMPLE 独立新回合固定 controller、reset/任务合同、feedback tier 和入口版本；配对原版/候选记录动作数、最后回执、新观测、turn 终态、审计与视频。网络分支只在闭合网络错误可确认时评估；没有真实断线就记“该分支未物理验证”，不制造未知物理重放。分别评估连续性与技能选择，不能用两个同时变化归因收益。比对门推开/抓盒已有行为不退步，并保留苹果侧抓、放盒阶段、水龙头机制的失败反例。

新回合第一条公开说明列实际选用原子经验、未选原因、当前兼容性及要重查的观察；空手步行/持物行走、抓起/释放、门推开/解锁分别验收。仅在新真实证据/合同变更/人工纠正后发一次候选或反馈：版本、公共路径/hash、前提、反例、不适用项、反馈 tier。请求发回 reviewer 辅助 queue，并逐项区分 ACK、集成和物理验证；无 ACK 不得打断进程。

最终交付补记：API actor.py 已由其 owner 并发增加原子写入、自然 completed-turn 处理及新run接线；本评审未修改或验收这些变化。INSTRUCTIONS 常量未变，ground 的静态组合长度结果仍成立；实际新run/完整新提示必须由API owner再核验。公共adapter/caller无漂移，见 evidence/snapshot-drift-final.json。
