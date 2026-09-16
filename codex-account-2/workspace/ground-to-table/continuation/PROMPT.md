当前问题：接续上一自然结束的地面拾取上桌任务，并处理已排队但可能尚未采纳的用户要求与独立审查。
总目标：原 setting 下，G1 有真实腿脚移动、抓起原红色地面物块、持物运输、桌面释放并稳定；与 SIMPLE 分支并行且共享已验证机制。
不可重犯的错误：不同时 resume 同一 thread、不截断推理、不把移动了桌子的诊断算正式成绩、不把架构提示词优化称模型权重训练、不写公共 core。

只在 /home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table 写本任务文件。先完整读取该目录 TASK.md、USER_UPDATE.md、PEER_HANDOFF.md、SETTING_REVIEW.md、STATUS.md/status.json，以及 reviewer/REVIEW.md 和 review.json（若已落盘）。复用 /home/galbot/lizekai/RSI/ref/ACCOUNT2_ROLE_SKILL_REVIEW.md，不重复相同研究。所有新模型进程仍由第二账号 run.sh 启动，固定 Astra/xhigh，无 API 或主账号回退。

先在公开日志逐项确认新增要求已读。运行中的 actor 必须完整等待，禁止同时启动重复 actor；旧回合可自然结束，但桌子偏移 0.55 m 的回合仅属 diagnostic，不算原 setting 正式尝试。在下一正式回合前恢复原桌位（table_only_offset_x=0），保留旧 manifest、录像、失败与审查记录。先修复 reviewer 已复现的虚假成功漏洞并回归，再启新回合。若 reviewer 指出的是与真实目标无关的过严次序限制，应分析目标语义，不能机械收窄用户目标；但物块失去抓持后的推抛、侧壁支撑和手托不能算成功。actor 与 host 真值隔离不能只靠提示词，须验证实际工具权限。

用户要求“基于原有 skill 同步更新”：保持原版与来源，更新独立任务 skill；精简非必要重复，明确前置条件、when_NOT_to_use、成功/失败证据、适用控制器版本。完整遵循 /home/galbot/.codex/skills/.system/skill-creator/SKILL.md，执行其适用验证。主 skill/harness 合计严格 <=831 words /6250 characters。不盲目照搬 RoboRSI 的 GT、skip-harness、共享文件临时覆盖行为。已有独立 reviewer 是事件触发审查，不必每步四角色调用。

共享机制候选写本目录 PEER_OUTBOX.md，给出代码/控制器/skill hash、机制、前置条件、when_NOT_to_use、独立 reset 与原始证据。通过第二账号 queue 发给 SIMPLE 唯一 core 发布 supervisor 01a0a867-d7aa-71f2-8547-e264d6d09ede；未经跨任务验证不覆盖 /RSI/skills/loco-manip-core。外部分支文件只读，不接管其任务。

推进有区分力的控制诊断与完整物理回合，避免已否决无新信息的脚目标重试。先读取 PEER_CONTROL_UPDATE.md 的最新 SIMPLE 控制反证，并核对其中原始结果，避免重复其幅值试验。不得在缺少外部授权时擅自换机器人、桌位、控制器、底层模型或动力学。若真正受这些边界限制而没有安全在范围内的下一步，停止并清楚提出最小待决项。

本接续器只在当前 CLI 回合完整自然退出后运行下一回合，不使用推理时间截止。每次退出前更新本目录 continuation/supervisor-state.json：status 为 continue/blocked/complete，附具体 evidence、next_step、running_sessions、reason。continue 必须对应已完成的实际进展与明确下一步，不允许空轮询/空模型重试；若仍有 tmux actor 运行，明确其 ID 并只等待/审查，不能再开同任务 actor。usageLimitExceeded 或协议错误必须 blocked，不重试、不自动用重置券。未产生新的状态文件时接续器自动停机。
