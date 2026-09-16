你上一个有边界回合已自然完成，本回合通过第二账号resume同一thread，继续处理积压的新用户指令。固定gpt-6-astra/xhigh，保留sandbox+自动审批，不开SIMPLE/其他环境、不读api.json/auth.json、不调用付费API、不新建子agent。

先读 ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md、ref/tasks/api-budget.json、codex-account-2/continuation/PROMPT.md。你之前的“预算尚未答复”已过时：用户明确授权所有并行角色/分支累计不超过10000元，每累计1500元汇报一次，报告不追加预算。API来源、计费仍未知，缺这一项阻塞付费调用，不阻塞SIMPLE。SIMPLE主控新公开日志已给出完整 R020-PARALLEL-SKILLS-20260916 ACK（包含“已读新增要求及预算文件”），请运行已有delivery_status更新，不伪造ACK。

请只完成以下有边界修正，仍由你独占 tools/coordination 与对应 R020 文件的维护：
1. 修正旧inbox、报告、README、coordination状态中的预算未知与ACK未到陈述，保留历史记录但标注被新事实取代。门槛读取唯一授权预算 ref/tasks/api-budget.json，不要求用户重复授权；来源和计费未知继续如实待机。共同核心由SIMPLE supervisor唯一发布，ground-to-table独立写域，直接复用已交付角色报告。你的waiter只做check/登记/ACK，不另造resume watcher；现有 rsi-simple-continuation-0916 已负责主控自然结束接续。
2. 实现最小共享预算账本与原子并发预留（单文件/文件锁即可，货币整数分），用于未来API分支：累计已结算+在途预留+本次最坏费用不得超过10000元；每次reservation有唯一请求id，重复请求幂等；结算/取消不能重复扣费或静默释放仍在途请求；阈值汇报每1500元，需持久化待汇报事件直到真正汇报。费用配置必须有明确提供方/模型价格/币种与换算依据，不能虚构价格或API来源。任何无法预先约束最大费用的实际请求不得发出。当前仅离线实现及测试，绝不新增真实费用。记录接口适配/实际计费验证仍待完成，不能宣称真实API runtime已验证。
3. 测试超上限拒绝、并发预留不会突破共享上限、幂等结算、未结算占额、重复/多阈值提醒以及来源缺失阻断。所有测试用隔离合成ledger，生产账本初始真实费用0不得被测试污染；保存测试证据。
4. 更新 artifacts/R020/coordination-status.json 和简短交付报告，明确当前推门0/3、付费调用0，已落实哪些离线约束、哪些条件待核实。不要再次研究MoE、不要改主控runner/控制器/公共skill。完成后自然结束，现有SIMPLE主控保持运行。
