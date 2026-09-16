# Skill 精确替换建议（未应用）

仅由 SIMPLE supervisor 在审查候选后应用到下一次启动读取的 skill。不要改历史 episode 快照/证据，不热修改在途进程。同步检查实际 campaign 的 local/assembled SKILL.md，避免 experience_read 继续灌入旧结束指令；保留旧版本、用户纠正来源与此次候选路径。

下列旧段均精确匹配 context/ 中的读取快照；替换整个段落，其他内容不动。自动改写时按 rsi.skill_learning.skill_size 检查 831 words / 6250 characters / 5357 non-whitespace；owner 的最终组装版本也必须单独检查。

## skills/loco-manip-core/SKILL.md

旧段：

```text
Await complete model and service responses; reasoning delay is not action failure. Simulation currently pauses during reasoning. Stop physical actions on rollout_finished. After at least three completed actions, finish_attempt can document an evidenced stall and changed hypothesis; it is never success. Do not fill the remaining budget with idle holds.
```

替换为：

```text
Await complete model/service responses; physics pauses during reasoning. While rollout_finished=false, continue safe tests within budget. After>=3 actions, finish_attempt records evidence and next_hypothesis only; test it now. Stall, low expectation or reasoning delay is not terminal. Stop for native termination, safety/system fault or budget end; avoid unchanged retries and idle holds.
```

以快照计算的替换后长度：477 words / 3835 characters / 3349 non-whitespace。

## skills/loco-manip-simple/SKILL.md

旧段：

```text
Stop actions on rollout_finished. After>=3 actions, finish_attempt may end an evidenced stall with a changed hypothesis, never success or merely slow reasoning. Avoid idle budget use. Then submit complete revised skill, concise lesson/change_summary, existing evidence and transfer_scope. Preserve versions, selections and failures within caps. Shared promotion requires cross-task validation and grasp regression.
```

替换为：

```text
While rollout_finished=false, continue safe tests within budget. After>=3 actions, finish_attempt logs evidence/next_hypothesis only; test it now. Stall/low expectation/slow reasoning cannot end episodes. After termination, submit full skill, lesson/change_summary, evidence and transfer_scope. Preserve versions, selections, failures and caps; shared promotion needs cross-task validation and grasp regression.
```

以快照计算的替换后长度：706 words / 6072 characters / 5350 non-whitespace。

生效边界：工具门槛由 candidate.patch 修复；skill 文案建议是配套消除冲突指令，不能单独修复已加载的 LearningHost。保留 episode0008 的 native=in_progress / policy_declared_stall 原回执，解释为主动提前结束，不改写成真实终态失败或成功。没有在本候选运行物理回合。

交付时并行版本说明：共享 SIMPLE skill 在本任务期间更新为含 episode0009 的经验；快照另存 `context/loco-manip-simple-after-drift.md`。旧结束段落未变，上述精确替换仍适用，保留新经验；按该后续快照替换后的长度为 695 words / 6005 characters / 5294 non-whitespace，仍满足三项上限。此检查不是对新经验的物理审计。
