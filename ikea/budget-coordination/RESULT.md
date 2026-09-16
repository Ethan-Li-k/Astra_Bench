# 跨分支预算修复交付

已完成并部署最小共享预算库修复；2026-09-16 09:27:26 UTC发布，SHA256 `9008e224d3161ecd952cdc507cf10aa344d5ecd7582be5fd57c19a20efe8551e`。仅新进程加载；没有恢复任何旧call，没有付费API、费用查询或仿真动作。

- 两个旧代码拒绝复现已通过：显式跨分支授权仍被foreign hold阻断；一次加载的旧模块在dispatch前遇foreign hold拒绝。证据：`tests/reproduction.log`、`tests/reproduction-result.json`。
- 最终49项离线测试通过：跨分支12进程竞争仅5笔能占满余量、7笔超额拒绝；一次dispatch、连续ID、未知/已完成hold保留、未授权foreign拒绝、审批/哈希/模型/输入输出上限、路径越界、原actor/hook假传输、登记持久化和全部旧预算回归。测试账本全部在本目录隔离，第一轮测试夹具输出上限错误及修正日志保留。见 `tests/candidate-results.json`、`tests/candidate-tests.log`。
- 修复添加哈希绑定的schema2批次与任务授权组，保留旧schema1。新授权明确引用真实IKEA任务文档和桌面session；不伪造用户批准新schema的原话。独立审批可并行；旧未知hold纳入合计，旧审批/请求文件保持原样。
- 宿主重启后部署前再次检查Python调用者，无ground/IKEA API actor。仅网页和既有watcher存在；未操作它们。`deployment.json`记录进程快照、旧批次兼容、原子发布及保护文件哈希。生产账本、旧batch/approval、ground actor/hook全部字节未改。

实际费用上界仍未由实测估算证明；保留empirical_estimate_not_hard_bound标签。全局文件锁和累计已结算+所有在途预留约束、1500元持久提醒、超估计结算暂停逻辑保持原样。账本整数分上限仍10000元；报告不增预算。

owner下一步按 `FORMAT.md` 和 `register_batch.py` 为**新**独立run绑定实际数据范围与哈希，加载发布版本再做自己adapter的离线检查。IKEA真实新调用由01a0a96b-06cc-7150-8c73-7b0897936b52负责；ground恢复owner现为01a0a982-cec5-71c0-b771-091c31df61f2，前owner随重启退出。原run/call55不恢复，旧未知费用不清空。

三方状态以 `state.json` 与消息回执为准：维护者已交付；queue成功仅是入队，真实ACK单独记录；库发布不等于owner adapter集成或真实API验证。本任务不无限等待ACK。
