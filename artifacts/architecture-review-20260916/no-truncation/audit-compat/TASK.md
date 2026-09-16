# NT候选逐turn记录与审计兼容：有界辅助审查
当前问题：SIMPLE publisher已应用无期限turn/start ACK和不确定提交锁，但此前自动确认闭合network failure续接候选不能保存/审计每个中间failed turn。
总目标：基于当前在线版本，离线复现→最小候选→实际caller和auditor联合验证→交付唯一publisher。
不可重犯的错误：不能热改在线actor，不能丢中间失败或让残缺记录计成功，不重发未知请求/动作，不改既有环境，不启动模型实验/物理/API，不使用主账号。

继续原reviewer角色，仅在本TASK目录新建候选/快照/测试/文档。其他目录只读；禁止应用到rsi/tools/skills或网页。先读取此前no-truncation INTEGRATION.md和continuity.patch，再读以下已知新证据，避免全盘探索：
- artifacts/R019/instruction-cap-integration/status.json
- artifacts/R019/recovery-20260916/permission-contract-fix.json
- artifacts/R019/public-atomic-experience-20260916.json（公开条件经验，shared core未晋升）
- 当前rsi/codex_app_server.py、tools/learn_grasp_skill.py、tools/audit_simple_campaigns.py、tests/test_codex_app_server.py及现有相关审计测试。
第一参考仍ref/GPT-as-Policy的已读同context持续rollout与closed_network_turn机制；不要拷贝其任意次数/时限上限。

明确边界：长度+审计检索+render-frustum已在门16/水龙头8走完真实调用链，不能回退它们。NT仅ACK等待和不确定锁已上线；新的thread/start workspace-write/on-request/auto_review合同修复是独立已测试修改，必须保留，不能拿旧快照整体覆盖。正在执行的门17/苹果8/放盒4/烤箱1均不触碰。

验收：
1. 先在最新基线+此前自动续接候选上复现中间failed turn缺失/编号或audit误验问题，保留失败日志。选最小可接线方法，使每个匹配服务端终态的turn按唯一编号/身份保留，包含失败及完成；真实caller、adapter、auditor一致，不引入框架或额外状态平台。若改审计，要明确区分旧格式与新完整性合同，既有无恢复成功/失败回归不变。
2. 确认闭合network failed +有效同host/backend/reset +物理进展且无待执行动作才可续接。不靠沉默或error notification重发；额度/权限/安全/物理预算仍终止；unknown ACK/reply、EOF、无终态不重试。新恢复静态提示+实际入口/runtime仍满足831words/6250chars/5357非空白，不能截断凑长度。
3. 实际run_episode配假transport/backend验证：failed→recovered completed文件齐全、身份/顺序正确、无提前close、动作只执行一次；未恢复失败、缺号/重复/错身份、最后无完整completed、写盘失败不能被auditor算成完整成功；不放宽独立reset、skill_update、host-success、completion-contract、人类辅助分层或审计检索。
4. 无新进展反复断线仍关闭现有caller的已知限制要明确保留；如果最小范围不能解决，不谎称现场持久保存。主机重启现场丢失不可用此候选恢复。
5. 只对修改相关测试以及原adapter/caller/audit必要回归运行；禁止新物理/模型/API。保留新的源哈希、针对性diff、测试回执、INTEGRATION和FINAL，写progress.json供主控查看。最终再次检查源漂移，不能覆盖并发修改。

交付只向唯一SIMPLE辅助publisher 01a0a867-d7aa-71f2-8547-e264d6d09ede 排队，使用codex-account-2/run.sh queue、provider=openai、gpt-6-astra/xhigh；说明候选未部署、验收边界、不要热改在途actor。API/IKEA现用不同API调用链，本补丁不可盲用。无需等所有机器人目标完成，不要监控循环；完成这个有界候选就结束。不得改旧no-truncation结果冒称全部上线。
