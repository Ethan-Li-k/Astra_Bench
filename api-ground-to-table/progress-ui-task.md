# 辅助账号：接入现有进度视频页并完成三方交接

只通过现有codex-account-2/run.sh、gpt-6-astra/xhigh执行。禁止主账号、额外模型代理、付费API、余额/配额查询、环境安装或启动/终止任何机器人任务。不读取凭据。适用AGENTS三行决策、apply_patch、长命令tmux+tee。模型限制时停止不重试。用户最新持续任务见同目录CONTINUATION-20260916.md，先读；当前工程师仍在API回合，不与其争写actor/budget/skill文件。

边界明确的两项交付：

1. 修改已有 /home/galbot/lizekai/RSI/human-feedback 的只读视频进展页，保留现有内容和关闭标注状态，新增API地面块上桌进度区。无需新框架、依赖、页面站点或Canvas；这是现有页面功能修复。先检查文件近期变化/owner证据；如其他写者冲突，只提交候选给其owner。主进程不变。可在验证通过后重启且仅重启已确认rsi-human-feedback-h001的UI服务，以加载新增只读API路由，保留旧日志；禁止波及其他tmux会话。
   - 来源 api-ground-to-table/actor-adapter/auxiliary-progress.json 和对应 campaign/episode-*/result.json，仅选公开字段；辅以公开stage/经验索引（存在才用）。别读host_audit返回浏览器。显示run/episode、当前阶段、API完成数、真实动作数、物理秒、更新时间、推理暂停状态、实际终态分类。未验证的抓取/搬运/放置明确“未验证”，不臆测完成。
   - 浏览器每10秒自动刷新状态，不重建正在播放的视频元素。阶段/回合终态变化时可见通知，不每调用弹窗，不依赖新模型请求；未观察到更新只显示多久未更新，不对推理设置超时或自动重发。不声称后台聊天通知已启用。
   - 显示首批episode0001已封口的真实视频。第二批/后续只有result与完成录像确实存在且ffprobe可读时才发布；录像未封口时文字说明，绝不修改正在写的视频。保留动态精确白名单、loopback/Host/Origin校验、防任意路径、媒体Range与source hash证据，不暴露凭据源码等。
   - 最小测试：无当前result/正常推理/终态预算截断不是失败/后台错误/陈旧状态/旧视频能Range播放/任意路径拒绝。复用human-feedback/tools已有测试，写新针对性测试，不泛化大型仪表盘。所有新证据 api-ground-to-table/progress-ui-verification/，写最终UI-RESULT.md以及状态JSON。若>60s任务用tmux。

2. 通过现有辅助渠道落实协作（不调用主账号桌面消息工具）。阅读 artifacts/architecture-review-20260916/HANDOFF-API.md 和新memory-priority交接。向辅助审查线程01a0a94d-6143-74c0-80cd-03d0b61acaf0用codex-account-2/run.sh queue发简短用户最新方向及API证据索引，说明本分支已排队ARCH-REVIEW-20260916-V1-API给执行工程师，未ACK不能声称集成。不要并发resume。
   - 在已证实会被消费的 artifacts/R020/supervisor-inbox.md 用apply_patch追加本次交接（不要覆盖其他消息），请SIMPLE owner提供经审查的控制/locomotion/站位/持物移动候选以及适用合同。不要求暂停SIMPLE或改变其预算/任务。
   - 向API辅助工程师01a0a948-10bb-7d03-8f1d-b1eeda7cb93c通过其现有辅助queue转发CONTINUATION-20260916.md和UI进度入口，要求在下一自然边界消费交接、记录ACK、共享本地经验并继续同任务的下一次有区分力尝试，严格保留批准/预算/数据/安全边界。不打断当前API，不热改actor，不替其发API。
   - 保存各实际queue回执和精确文件段哈希；不把排队称为ACK。如果辅助queue不被活跃长turn即时消费，记录真实限制，不终止/resume规避。收件人可在当前回合结束后自然处理。

完成上述小改动、测试、服务验证后结束本UI工程任务。不要花模型额度反复轮询机器人。最终报告中文简短，包含可访问URL、测试、是否重启UI服务、其余机器人进程未动、交接真实状态。主负责人会打开页面做视觉核验。
