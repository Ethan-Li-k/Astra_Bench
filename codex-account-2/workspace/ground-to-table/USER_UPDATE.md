# 用户最新补充与并行分工

原用户补充（2026-09-16）：指定原会话已成功抓红块10次并停止该桌面抓取任务；仔细阅读并尽可能借鉴 /home/galbot/lizekai/RSI/GPT-as-Policy 与 /home/galbot/lizekai/RSI/ref/RoboRSI 的skill写法和主要思想；评估是否可以单独训练 planner/manager/engineer/reviewer、是否需要类似MoE；基于原有skill同步更新；与 codex://threads/01a0a4fb-3324-7073-b667-4e0e94c54ff2 并行，作为两个agent，各可有subagent。

这补充原TASK.md，不取消地面红块放桌。不要重复已完成的桌面10次目标；原成功公开经验可按权限检索并验证迁移。另一会话名称是 simple开门branch，已向其发送分工：它负责SIMPLE主线与共享core发布，本分支独立地面红块任务，只提交共享候选、评测证据与review；现有 rsi-skill-review-0916 已在做角色/skill研究，先读取已有成果，避免重复成本。

请现在在安全边界采纳本更新。需要时以第二账号run.sh创建具体限界的planner/reviewer子进程，固定gpt-6-astra/xhigh，tmux+tee；当前supervisor的multi_agent关闭不妨碍通过同账号独立CLI分工。不要从主账号工具生成subagent，不要每动作机械调用四角色。角色分工先验证收益，真正训练需明确可训练目标、轨迹量、验证集、成本和底座；GPT技能/提示迭代不能称为已微调四个模型。是否MoE须区分神经网络MoE和明确的技能路由/条件调度，暂不下载训练新模型或启动付费API。

务必读真实代码/skill而非只读README：GPT-as-Policy的Direct SKILL、EEF contract、teacher_context、history/NOTES/run；RoboRSI的agents/planner.py、engineer.py、reviewer.py、manager_chat.py、skill_selector.py、skill_synthesizer.py、task_wiki.py、agent atomic/long_horizon lifecycle以及一套atomic skill/wiki。按任务需要选取，不把上游的物体真值、点云权限、其他模型或真人审批流程默认导入本项目。

尽快写一份简洁 ROLE_AND_SKILL_DECISION.md，用具体来源路径和机制说明采纳什么、拒绝什么；让研究落实到本分支task skill、选择/经验索引、失败复盘和受控shared candidate，不仅写架构报告。技能主文依旧<=831words/6250characters，细节放按需参考，保留版本和出处，独立review验证实际控制/视觉权限及成功证据。读取新文件前先查看已有peer成果，公共共享文件保持单一发布者。

同目录 PEER_HANDOFF.md 若出现，是另一会话的进度与可复用路径；每次新回合前检查。本分支给peer的交接集中写 PEER_OUTBOX.md，包含技能候选、适用前提/禁用条件、版本hash、公开证据、失败反例，不能将坐标目标/隐藏真值混入actor经验。当前不热改正在执行的actor。
