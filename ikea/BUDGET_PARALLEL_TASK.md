# 原预算维护者的新有界任务：支持明确授权的跨分支并发

用户本轮明确要求IKEA现在利用API、辅助账号并行推进，与SIMPLE、地面搬运共享经验。见 `ref/USER_UPDATE_20260916_IKEA_OWNER.md`。仍累计10000元、每1500报告，不查费率/余额，不自动消费重置券，不触碰凭据。只用辅助账号固定gpt-6-astra/xhigh。

你继续作为 `tools/coordination` 原维护者。已有actor `api-ground-to-table/actor-adapter/actor.py` 在main中一次load_module预算hook，hook一次加载shared_budget；因此正在运行ground002的进程内仍是旧代码。当前reserve_empirical/begin_empirical拒绝foreign unsettled batch；reviewed_batch还固定旧单条审批引用。**不要现在往生产账本加入IKEA预留**，否则旧ground下一call会终止。不要修改ground在途代码、batch/approval hashes或注入进程，不取消未结算费用。

请在 `ikea/budget-coordination/` 保存候选、测试、进度和交付。先写两个有界复现：现有代码拒绝明确授权foreign并行；旧内存代码遇到新foreign hold会被拒绝。再对当前shared_budget制作最小候选，支持哈希绑定、显式授权的跨分支批次，保留未知费用/已完成hold、全局锁与合计上限、连续call_id、一次dispatch、输入/输出上限、旧未授权batch拒绝。不要虚称实测预留为硬价格上界，不凭空造用户逐字批准某份新schema的记录；可引用本次确切授权文档与桌面会话id。

保持旧数据可读，与现有actor传输兼容。必要的离线验证覆盖跨分支竞争额度/上限、不确定请求不重发、篡改审批/hash/模型拒绝、旧批次回归，不能用生产账本做合成测试。现有完整turn/自然物理回合边界之后才能部署到新进程。请联系ground辅助工程师01a0a948-10bb-7d03-8f1d-b1eeda7cb93c，协调其自然结束后下一批次加载修复；联系IKEA辅助工程师01a0a96b-06cc-7150-8c73-7b0897936b52，告知暂不能在旧ground在途时加入生产预留、可继续辅助账号物理探索。三方ACK与实际上线分开。

可以做候选与交付，不要在本任务发送付费API、启动仿真、修改其他共享runner或建立新角色框架。部署前证实现有调用者都兼容；如果安全边界尚未到，留下可供唯一发布者接续的候选和明确状态，不无限等待。所有长任务tmux+tee，每次决策三行。任务结束写 `ikea/budget-coordination/RESULT.md` 与 `state.json` 并向IKEA辅助线程发queue。直接完成有界修复工作，不重复调查费用或主账号桌面通知。
