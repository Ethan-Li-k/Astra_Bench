# 2026-09-16：禁止人为截断推理；GPT-as-Policy第一优先级；三任务共享经验

用户原话：
“给三个账号发指令，说明任务推理不可以被截断而停止，当前截断现象严重，参考/home/galbot/lizekai/RSI/ref/GPT-as-Policy中的解决方式，这是我们参考的第一优先级，你需要根据其他对话的实际情况不断根新skill，确保skill的更新可以与任务相适应，三个进程可以共享经验”

本轮三任务为SIMPLE、地面物块搬运、IKEA场景探索。模型执行继续只走辅助账号或既有授权API，固定gpt-6-astra/xhigh；禁止主账号模型进程、自动降级、自动重置券。安全、不可恢复系统错误、usageLimitExceeded及既有总预算/明确请求授权仍是边界。本要求不把预算截断改称失败，也不授权悄悄超出总额。

## 推理与回合连续性

1. 在途推理完整等待，不因wall-clock耗时、估计chunk延迟、短时间无动作/日志、暂时低成功预期而终止、取消或重复请求。状态应明确标注inference_waiting，不误报卡死。
2. 区分模型推理等待、RPC建立/网络故障、动作跟踪到位超时、物理回合预算、API请求授权/费用边界、模型自然turn完成、策略主动提前结束。每次停止保存准确stop_reason、最后ACK/observation/step、是否仍在推理、是否可继续；完整任务未完成不能只写done。
3. 模型自然结束一轮但物理仍in_progress：在确认旧turn已结束后，保留同一thread、同一仿真和同一reset，携带最新公开观测、NOTES/阶段进展及next_call继续。不得因任意短continuation次数或代码for-loop耗尽就将任务结束。连续没有有效进展需要诊断/重规划，不无限消耗空turn；不重置掩盖中断。
4. 网络恢复先核实旧turn终态/服务器状态；只恢复已确认结束的请求。保留仿真、历史和动作ACK；已执行动作不重放，结果不确定的物理动作不重试。传输歧义不得用新thread/并发resume绕过。额度/授权/安全/真实物理故障停止不属于可自动重试的网络错误。
5. 不能热改当前在途回合或停止进程以应用修复。记录生效边界；在自然边界验证后启用。已宣告预算边界保持原回执，规划后续可执行预算/状态保存，不伪造同回合无缝续接或擅自超额。

## 第一优先级参考及已核对的边界

以本地 `ref/GPT-as-Policy` 为第一优先级，RoboRSI第二。重点阅读：
- `hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md`：持久上下文，NOTES/scratch，rollout_finished=false继续，低成功预期不能提前结束。
- 同目录 `context/teacher_context.md` 和 `context/eef_control.md`：任务知识与控制合同分离，实际ACK及观测证明进展。
- `hybrid_rollout/robodojo/skill/run.py`：`_network_continue`、`closed_network_turn`和同thread/同仿真恢复；恢复前确认旧turn已结束，不回放动作。
- 同目录 `transport.py`：EOF/线程通知和RPC失败区分。

注意：参考当前版本仍含900秒timeout、最多2次普通continuation及有限网络重试；不能把这些数字照搬为本项目推理停止条件。当前RSI `rsi/codex_app_server.py:run_turn` 已使用 `next_message(None)`，实际截断必须继续查caller/停止门槛/故障记录，不能重复声称修掉了已不存在的超时。参考中的模型、夹爪数值、机器人、GT或预算失败分类不覆盖本项目约束。

## 与实际任务同步的技能更新

每次完整物理回合、可复现系统故障、任务合同变化或明确人工纠正后，先审阅实际公共观测/动作/ACK/录像与隔离host审计，再更新本任务skill候选。共享publisher仍唯一；每回合pin版本，新版在下一安全边界生效。保留旧skill、失败、来源、长度证据，主skill+运行合同<=831words/6250characters及既有5357非空白检查。

每个新任务/回合开头明确选用的原子经验ID/版本、来源公共轨迹、适用前提、反例、不适用条件和本轮需要重新确认的条件。按控制合同→locomotion→交互机制→任务实例共享。支持locomotion→manipulation→locomotion组合，但空手行走≠持物行走，抓起≠稳定携带/释放，推门≠转把手解锁，SIMPLE修复门框的成功≠IKEA原场景成功。没有兼容证据就明确不迁移。

审计否决/未知/回合不完整/合同不匹配的原生success不作为成功优先项，仍保留作反例；host隐藏真值不进入actor经验正文。人工语义反馈回合单列。参考已有架构候选与memory-priority补丁，避免重复开发或覆盖completion_contract/staged-placement/finish与部分动作异常保护。

三方每次接到本指令写公开ACK：`NO-TRUNCATION-SHARED-SKILLS-20260916 ACK`，列当前thread/run/episode、实际截断类别、在途回合是否保护、准备应用的版本和证据路径。将后续公共经验与问题送至架构维护者辅助thread `01a0a94d-6143-74c0-80cd-03d0b61acaf0` 的正规辅助账号queue；无需唤醒主账号桌面任务。只在有新证据/新候选时发消息，不逐请求或无变化刷屏。排队、ACK、代码集成、物理验证分别记录。
