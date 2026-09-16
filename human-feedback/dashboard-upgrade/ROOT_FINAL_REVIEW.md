# 根审阅：交付前必修（用户既有授权范围）

当前问题：四任务页已上线且录像可播放，但已核实的负责人/来源改变尚未反映到最终交付。
总目标：让网页答案送达当前owner，卡点/框架结果真实可读，并在现有UI内完成小范围修正。
不可重犯的错误：不截断任何当前turn，不启动机器人或付费API，不把排队当ACK，不扩大目录暴露。

本文件由当前主控明确下达：已根据该任务公开恢复记录和owner ACK核实收件人更换，授权将ground固定白名单更新为下列现任辅助owner。此项覆盖初始TASK.md里旧ID限制，不需要再向用户确认，也不要只留下“待主控确认”。不扩大其它任务或第三方目的地。

1. `feedback_board.py OWNERS[ground]` 仍为旧01a0a948...，现任辅助owner已由 `api-ground-to-table/actor-adapter/auxiliary-progress.json` 的owner_thread/recovery_owner_thread及 recovery-20260916/RECOVERY.md确认为 `01a0a982-cec5-71c0-b771-091c31df61f2`。把固定名单更新到此已核实owner，同步OWNER_INTERFACE，向此新owner发一次UI工程交接（旧回执保留，不自动重投历史用户回答）。固定provider=openai确保辅助路由。测试使用stub，不向真owner发测试答案。
2. `dashboard.framework` 仍只读旧status，文案“正在审查”已经陈旧；`no-truncation/progress.json` 与result.json已明确18项离线测试通过、三入口排队、待唯一publisher发布、candidate_applied=false。读取现有公开结果/进度字段，页面显示“离线验证/已交付；待集成与物理验证”，不能把审核等同发布。不额外开模型。
3. SIMPLE门15公开动作约08:56UTC后无新动作/无终态，页面现在的下一步“继续下一回合”不足以说明真实等待。对于active-unknown显示“当前回合终态和执行状态未确认；由SIMPLE执行者核对在途turn/进程，再决定同回合续接”，既不推断已经死，也不声称仍在推理。支持各任务已有public-progress中的短 `current_problem` / `next_step`（或已用同义字段）覆盖通用文字，以便owner未来直接更新卡点；没有提供时清楚标明尚未上报。接口文档追加这两个短字段，最小实现不要新状态平台。
4. 已排队的 liveness-review、ground-owner-review、help-evidence-review内容适用。冷启动三回合求助的同回合媒体绑定与不同媒体拒绝请确认相应测试覆盖；已解决不要重复做。

根浏览器已实测8765四lane出现、door14录像duration92.64能播放+右键跳转、apple7新录像出现。你现有浏览器QA继续，无需重做未变化的全部检查。只补必要回归与实际页面快照并再次由身份验证脚本重启UI。保留既有交付物，结果写 ROOT_REVIEW_RESULT.md；完成后结束，不无限跟随其它机器人任务。

最新主控协同证据：SIMPLE桌面负责人刚明确报告同宿主boot切换、09:46核实无SIMPLE runner/主管/watch，原door15缺终态，判基础设施中断；现仅第二账号恢复原主管01a0a867...于rsi-simple-recovery-0916。禁止UI另起恢复。该确认写入root-simple-recovery-handoff.json，优先读取随后owner公开状态；若尚缺更新，可在UI引用此明确标“负责人报告”的公开协调摘要，待原owner状态新于此记录后自动优先原owner。不再声称原door15仍在等待推理。

用户最初关心的前置桌面拿块10次已经在artifacts/architecture-review-20260916/status-evidence.json tasks.table_cube核验：verified=10/physical_attempts=15/endpoint_retained=5。只在SIMPLE旁或历史里补一行“前置桌面抓取：10次原生成功（终态仍持有5次），学习成绩”，不能混入SIMPLE计数；不新增lane或重跑旧实验。
