# R020 预算与 ACK 修正交付（2026-09-16）

预算已确认：所有角色/环境/分支共享累计10000元硬上限，每累计1500元汇报，汇报不续额；唯一授权源为 `ref/tasks/api-budget.json`。旧预算/ACK陈述已修正，旧交付保留于 `history/` 并标注被新事实取代。

主控的完整公开 ACK 已由原 delivery_status 工具识别，并再次核对原日志事件SHA256/字节偏移，包含“已读新增要求及预算文件”；见 `ack-verification.json`。不是仅入队。本轮没有重发相同消息或resume主控。

`tools/coordination/shared_budget.py` 已实现整数分、单一共享账本与原子文件锁预留；已结算+未结算预留+本次最坏费用不得超过上限。请求ID、结算和取消幂等；在途不能直接取消/超时释放。每1500元及最终上限产生持久化待汇报事件，真实发送证明确认前不清除，汇报不改变费用或上限。缺来源/价格/币种/换算依据或不能约束最坏费用时拒绝预留/发出登记。

41项离线测试通过：15项预算、22项门槛、4项ACK。并发8个各2000元合成预留仅5个获准；同ID并发只占一次。超上限、未结算占额、幂等结算、取消限制、多阈值/重复提醒、缺来源、过期/变更价格及无界费用均覆盖。所有费用/账单/发送证明为隔离合成数据；生产账本测试前后哈希不变。证据见 `budget-test-evidence.json`、`budget-correction-tests-final.log`。

当前：推门真实独立审计0/3；生产已结算0分、在途预留0分、付费调用0；IKEA待机。API来源、模型价格、计费/换算依据、可强制请求上界、提供方适配与实际对账/汇报、远端统一账本接入仍待核实。没有真实API runtime验证，不发付费请求；这些条件不阻塞SIMPLE。

R020 waiter只check/登记/ACK，已原位恢复tmux+tee。主控接续仅归既有 `rsi-simple-continuation-0916`。共享核心仅由SIMPLE supervisor发布，ground-to-table保持独立写域；复用角色报告，未新做MoE研究，未改runner、控制器、公共skill，未新建环境或子agent。当前可恢复状态见 `coordination-status.json`。
