# R020 bounded coordination work

当前问题：主 supervisor 活跃；IKEA 门槛与新增要求送达尚无独立交付。
总目标：独立本地研究、零模型调用的证据门槛、不中断推理的单次后续交接；SIMPLE 由既有 supervisor 继续。
不可重犯的错误：不重复 campaign、不读凭据、不改控制器/runner、不删诊断、不计回放/自述成功、不把未验证 locomotion 当已掌握、不同时 resume。

决定：只读参考实现、有限必要交接与公开 supervisor 日志；新实现限定 tools/coordination、artifacts/R020 和指定 ref 报告。测试数据独立标记 synthetic，生产门槛禁用 synthetic。

当前问题：文件计数和 result.success 不能证明真实独立成功，旧回合也未保存完整的进程重置 provenance receipt。
总目标：只在可信 host 登记后重算接触、角度、保持、站立、完整终态与推理完成；缺项拒绝。
不可重犯的错误：不能补造旧 provenance；不能让单个成功录像复制三次；不能把测试夹具写进真实 ledger。
决定：生产入口固定 R019/door-campaign，host receipts 由既有 supervisor 审查实际启动/重置记录后提供。R020 不自动认领旧文件；信任边界公开说明。正规 queue 已成功，无需并发 resume 或进程注入。

当前问题：辅助交付已验证；生产门槛0/3，supervisor只有正规queue回执尚无明确ACK。
总目标：交付可恢复入口，独立等待真正证据和用户API配置，让既有supervisor继续SIMPLE。
不可重犯的错误：不得把26项单元测试、合成正例、queue成功或视频元数据检查误报为物理成功/已读。
决定：26项测试通过后启动rsi-r020-coordination-wait；只登记、不启动模型/仿真；checker每60秒维护gate与ACK，主账号不轮询。完整交付、测试局限和待确认事项已存coordination-status.json。Canvas仅源码检查，未声称已渲染。保留全部诊断。

当前问题：预算与ACK已有新事实，旧交付表述过时；需补共享预算原子预留离线约束。
总目标：以ref/tasks/api-budget.json为唯一授权源，累计10000元硬上限、每1500元持久化待汇报；来源/计费未知不发付费请求。
不可重犯的错误：不要求重复预算授权、不将queue当ACK、不覆盖主控/ground-to-table写域、不造真实费用、不另建resume watcher、不让在途请求被静默取消。
决定：保留本次修正前交付快照；只实现独立本地账本和测试，生产费用从0开始；主控与continuation归属不变。

当前问题：预算和ACK已按真实新证据纠正；共享预留只完成离线验证，来源/计费仍未知。
总目标：在不触碰主控和独立环境的前提下交付可恢复账本及门槛状态。
不可重犯的错误：不能把41项合成离线测试当真实费用/API runtime验证；不能把预算10000元分配成每环境10000元；不能让报告续额。
决定：生产账本保持已结算0/在途0/请求0，测试前后哈希不变。R020 checker原位恢复，仅check/登记/ACK。真实主控ACK已核验；主控与唯一接续器仍在。余下来源、计费、上界实施、实际对账与跨主机接入列为未解决条件。本次有边界修正自然结束。

## 门框修复版本登记兼容性
当前问题：正式asset003推门已使用经审查的四box固定门框修复，旧receipt强制original_physics=true与事实冲突；0010/0011有主控成功审查，未签发登记收据。
总目标：保留旧schema，增加严格绑定唯一修复ID、source mesh和验证证据的新schema；复用原物理审计及独立性/完整性门槛，交付精确格式供主控签发。
不可重犯：不将修复称原样native CloseDoor，不代签、不将2写成3、不计0012、不启动IKEA；不查费用、不改campaign、rsi、公共skill或接续器。
当前问题：旧常驻零模型waiter已加载旧schema，会将主控未来签发的v2拒绝；默认check还会读取本任务明确排除的API/费用状态。
总目标：同一个现有waiter重载新审计，使用physical-only检查与原ACK读取；不增加进程角色或resume机制。
不可重犯：不得重启主控/actor/接续器，不创建第二waiter，不调用API或查询费用；不存在旧waiter时只报告未运行，不擅自另起。
当前问题：schema2和两个已审查回合的离线预检已完成，真实登记仍需主控签发；不能把预检当授权或第三次成功。
总目标：以frame-override-review-delivery.json和精确格式文档交付，保留独立来源、严格门槛、旧schema及全部原证据。
不可重犯：不代签/登记，不读取0012，不启动IKEA；不因API/费用问题阻塞或扩展本任务，不修改其他线程。
交付完成：41项离线测试通过；audit_trace/video_probe AST未变；原schema1模板、生产registry及已绑定0010/0011证据未改。原零模型waiter已重载physical-only；主控/actor/接续器未触及。真实host收据仍由主控负责。
