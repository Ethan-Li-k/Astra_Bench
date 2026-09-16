# 连续性与任务适配：有界交付

已完成 **NT-20260916-v1 候选，未合并、未运行物理验证**。在线 rsi/tools/skills、UI、既有回合及前两轮评审文件均未修改。

- 查明近期 SIMPLE 三个操作回合是物理预算结束；门15先有网络断线通知、没有 turn终态，随后主机重启。API搬运恢复 owner 已确认重启中断，第55次请求结果未知；不能自动重发。IKEA仍无 actor 物理尝试。详见 [FINDINGS.md](FINDINGS.md)、[原回执分类](evidence/outcomes.json)。
- [continuity.patch](continuity.patch) 仅改 adapter：确认闭合且有新物理进展的网络失败在同 thread/backend 内继续；无新进展进入诊断；取消 turn/start 的900秒ACK期限并锁住不确定提交。既有无期限推理等待、finish_attempt、执行异常、completion_contract/放置及审计检索候选保持兼容。
- 原版先复现 **4 failed + 1 error**；候选 **18/18 离线测试通过**（10边界、7原测试、1实际caller配假 transport/backend）。三份任务技能结构校验通过；SIMPLE和ground实际runtime组合长度合格。IKEA仅验证拟用runtime，正式接口仍待owner确认。[检查](evidence/checks.json)、[长度](evidence/length-validation.json)。
- 前一 `combined-compatible.patch` 后接本补丁，在当前源副本上零fuzz dry-run及语法检查通过；最终检查发现 API owner 并发修改 actor.py；公共 adapter/caller 未漂移，API 的 INSTRUCTIONS 常量未变。保留其新代码，本轮没有替它验收新授权或完整行为。详见 [最终漂移](evidence/snapshot-drift-final.json)及[影响核查](evidence/api-drift-review.json)。[兼容/漂移证据](evidence/compatibility.json)。短技能和公开条件经验见 [skills/](skills/)、[接入顺序与验收](INTEGRATION.md)。

SIMPLE公共publisher负责逐hunk审查和自然边界发布；API/IKEA owner负责各自合同和实测。三个已授权辅助入口的排队结果见 [delivery-receipt.json](handoff/delivery-receipt.json)。排队不是ACK；首轮ACK和本次收到的新证据另见 [incoming-receipt.json](handoff/incoming-receipt.json)。API恢复owner已经变更，只要求原有协作链转交，不唤醒旧线程、不自行增加收件人。

当前没有物理收益、部署完成或重启后无缝恢复的声明。缺少 terminal 的网络通知、未知 RPC、重启丢失状态、无进展反复断线仍需原owner诊断；预算/额度/安全停止不自动重试。没有新模型/API调用、仿真、环境修改、子代理或主账号工具；本评审启动配置由本目录 run.sh 指向 account2、gpt-6-astra/xhigh。
