当前问题：用户明确要求先停IKEA探索及地面搬运、集中六类SIMPLE任务，并复用已有skill。总目标：先完成可验证的暂停收尾，然后交付六类短skill/验收安排。不可重犯：不把PAUSE/队列当作已停，不丢轨迹，不盲重发未知API；不重新探索已知结论，不绕过主账号禁用。

你是现有辅助架构审查者，同一第二账号openai/gpt-6-astra/xhigh。不创建新角色/子代理/监督器、模型实验或付费调用，不启动任何物理新回合。原IKEA和搬运负责人保留，但当前两个continuation/PAUSE已设；SIMPLE原publisher唯一调度。先读ref/USER_UPDATE_20260916_SIX_TASK_FOCUS.md与本目录pause-delivery.json/simple-focus-delivery.json。Grasp入口用户澄清待回复，其余无需等待；原91范围已经被本阶段六类覆盖。

最高优先：完成“暂停”而不只发通知。
- 地面分支api-ground-to-table/recovery-20260916/progress.json当前episode005已结束HTTP429、actor_alive=false、没有在途推理，supervision watcher只阻塞休眠。核对进程身份/启动ticks与绑定；证明没有新请求/物理在跑，保留未知请求和已封口视频，不重启其owner/actor。保留PAUSE，不动共享预算/认证。不必为了闲置watcher消耗新模型；可保留零模型休眠监控。
- IKEA apple0002仍在跑，tmux rsi-ikea-subscription-apple-0002，owner01a0a96b-06cc-7150-8c73-7b0897936b52；continuation owner当前也可能在途，heartbeat零模型。读取当前精确进程树、启动时间、runtime/episode绑定、最后动作/模型状态。先检查现有安全暂停/取消接口；用户本次明确暂停覆盖该支线旧自动继续要求。优先在最近已完成物理工具边界终止后续动作/请求并保留录像。如果没有可用优雅暂停入口且进程会继续新调用，可依据本次明确用户停工授权，对已双重核验身份的IKEA actor及仅该支线的管理进程执行最小定向取消/优雅信号，记录user_requested_pause，不称网络截断/物理失败。绝不按名称广泛pkill、不杀共享服务/SIMPLE/其他账号；SIGKILL不用作正常收尾。已有请求若取消后远端结果未知如实留存且不重发；不要等整段长探索继续花额度。无需另问用户是否允许暂停，已明确要求。
- 先保存原state/actor-progress/进程与动作记录，再收尾，检查录像封口、完整/不完整推理证据和所有仍存活子进程；不能捏造完整turn或成功。更新暂停公开状态/回执在本目录pause-status.json；必要时在IKEA既有state和公开进展只添加用户暂停字段并保留原state快照，不改原episode result/轨迹事实、不改正在执行的代码。暂停后不自动恢复。若自动审批拒绝，保留具体原因报root，不尝试绕过。尽快写progress供root确认已停/仍在途。

暂停确认后，限界审阅并准备六类skill方案（可独立任务局部候选，不发布共享core）：
- 复用artifacts/architecture-review-20260916/REVIEW.md和refs；ref/GPT-as-Policy首优先，短共同控制合同/NOTES/实际执行反馈；RoboRSI第二，不重新研究平台/MoE/多模型训练。主harness+skill831words/6250chars/5357非空白，保留版本证据。若创建/修改SKILL.md候选，读取已有skill-creator SKILL.md并遵守实用规范，用户本项目长度/授权规则优先。
- 读取现有task-inventory/native-task-criteria、已完成table10、door10、bendpick6、XMovePick3及XMovePickSim1审计/公开skill；host审计仅review用不可进actor。当前SIMPLE真实调用保持唯一原supervisor，不碰campaign源码或热改其skill。
- 任务族XMovePick、BendPick、Handover、Mobile P&P、Grasp、XMoveBendPick：给出注册名候选/现有campaign/历史达标和人类反馈层/当前仍在途/每个有限阶段和可观察门槛。BendPick与SimToReal变体、Handover各变体不能混成绩。Grasp入口待用户，不能自行选MP示教轨迹或新机器人；最多两种入口映射待确认，准备公共抓取模块即可。
- 重点复用：可见包络→闭合→小抬升→独立留握/再观察；稳定站位、腕姿和全手净空、相机标定、测量/目标分离。门成功只能迁移可验证接近/稳定支撑/渐进接触方法，不能当持物步行成功。机器人本体字段已经在XMovePick3首动作验证且有新完整成功audit，不重复等值诊断，不把并变成功归因新字段。
- 分阶段解释timeout：XMoveBendPick1=49动作46timeout且命令闭合0；BendPickSim1=65动作44timeout、18动作含闭合；物理预算终止、不是同因抓持失败。复用当前memory/v1排除项，改进skill针对可见运动/追踪误差与阶段解释。Handover必须分别审原生reward触发、交付前承载、接收手支撑、交出手释放后的保持；若原生仅接触即成功，原生信用与真实转手证据分开，不悄改原标准。Mobile分离空手接近和持物运动/放置，现有mobilecheezit继续；无持物行走证据不能预置已掌握。
- 输出一个简洁review/六类任务执行说明和最小可复用模板；不为六类拷贝六份同样巨长主skill，不加泛化平台。学习与冻结测评分开，已有成功作历史基线，不凭旧回放加新成功。每个新正式评测pin任务/接口/skill/controller/seed/feedback/version，失败与视频保留；新任务最低成功数沿用已有每类1，不擅自升级10次或创建大量评测。
- 向唯一SIMPLEpublisher 01a0a867-d7aa-71f2-8547-e264d6d09ede 经run.sh queue送一次重点审阅/候选交接，Astra/xhigh/openai，工程回执与actor公开候选分离；不得发桌面send_message_to_thread。原三owner若仍活跃无需再重复通知。

结束条件：pause-status有可核验实际状态，六类短skill/任务合同建议及待澄清项完成，必要候选长度有证据，交接已排队（不假称ACK）；保留progress.json、FINAL.md、result.json、备份与验证。完整结束有界工程turn，不等待SIMPLE所有物理目标完成、不接管其现场调度。