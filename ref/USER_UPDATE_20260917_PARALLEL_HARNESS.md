# 并行执行与共享经验：用户最新指令

用户要求：打开并行，优化 harness 方案，同步尝试，共享经验。

- 两路物理继续由唯一主管管理：handover-place-back-sim-campaign 与 bendhandover-campaign；同任务写锁禁止重复启动。只用隔离辅助账号 Astra/xhigh，API及主账号禁用。
- 原中央owner已恢复并行工程，独立候选与状态在 artifacts/parallel-harness-20260917/central。重点是成功经验实际加载、抓持前腕姿空循环、handover阶段监督与必要工具往返缩减。
- 共享的成功前缀/失败首因/适用条件经中央一次验证与版本发布，在新回合使用；不复制场景坐标、不热换在途actor输入。
- 唯一物理主管读取这个共享目录的status.json/HANDOFF.md，不等待已满消息队列的ACK；原路径与队列历史保留。
- 已成功一次的精确学习任务退出；明显卡住的难任务暂缓，下一空闲槽选简单相似未成功任务；复核与下一任务执行并行。
- 完整等待模型返回，不因延迟重发。任务进展按实际阶段证据评估；微小腕姿改变不等于抓取阶段进展。

- 下一简单任务由独立辅助helper准备：artifacts/parallel-harness-20260917/next-easy/status.json与HANDOFF.md；只写候选，中央/原主管负责正式接入。BendHandover episode-0001已26动作后身体失稳终止，保留经验，下一回合须有具体修正，不能原样重启。

- v8.11已发布并已在bendhandover-campaign/episode-0002真实加载：新HandoverSim1经验与空手调姿反例、handover-goal-progress-v1均已绑定。只做这一次改变假设的复试；原PlaceBack1保持在途旧版本。原主管负责结果复核，不重复启动。回执artifacts/parallel-harness-20260917/execution-verified.json。
