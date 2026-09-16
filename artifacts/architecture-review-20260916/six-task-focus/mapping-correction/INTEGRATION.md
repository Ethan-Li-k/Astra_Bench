# v2 集成交付边界

唯一 publisher：`01a0a867-d7aa-71f2-8547-e264d6d09ede`。本目录 **candidate_only，未部署**。v1 暂定映射已被取代，历史原件和归档均保留；不执行其中暂停脚本或旧任务建议。本轮不改在线 rsi/tools/skills、campaign、页面或进程。

1. 到自然回合边界再审核候选。以 [host-contracts.json](host-contracts.json) 的六个精确 env_id 对齐既有 task specification；这是审查文档，不是可直接加载的 runner 配置。原生与独立语义合同分开。MP 两入口由 publisher 先做资产/根关节/地面基准/手型/执行器语义兼容检查；本轮无 MP adapter，不绕过准入、不使用示教策略。
2. 保留有效现有 XMovePick skill。需要时摘取适用段落，或选择 `candidate/loco-manip-direct/SKILL.md` 加一个换行与**一个完整** `candidate/deltas/<task>.md` 组合。不是安装六个重复主skill或覆盖shared core。每个 delta 的 task 必须与实际 env_id 完全一致；不得以 Teleop/Sim/Cheezit 变体替代 MP/BetweenTables。
3. 只复制所选 actor markdown 和经审核的公开来源到既有 allowlist。不得挂载本整个交付目录；host-contracts、审计报告、源码、source-hashes、version-v1和快照均不是 actor 输入。保留 human-feedback tier，否决/未知/反例保留原 outcome，现行 memory-priority 成功优先规则不回退。host 的合法来源选择或既有审计布尔标签不等于可暴露原始审计 payload。
4. 用当前 `validate_policy_instructions(final_markdown, immutable + NETWORK_CONTINUATION)`，给 `SkillMemory.runtime_instructions` 同一预留。当前源码快照、提取文本、每项完整 hash 和三项计数见 [checks/length-validation.json](checks/length-validation.json)。831 words /6250 chars /5357非空白同时通过才可使用；不截断。任意摘取后重新拼入旧skill、追加提示、MP适配改变runtime，都须重验**实际最终组合**，不能沿用本收据。
5. 五连胜稳定性/十回合冻结测评的加载隔离和计数由 publisher 实现并验证。本快照 [LearningHost:162](snapshots/tools/learn_grasp_skill.py:162)仍在终态写 memory.update；[run_episode:251](snapshots/tools/learn_grasp_skill.py:251)要求 skill_update。不得仅凭新文本宣称冻结完成：将建议/评价产物留在隔离区，固定加载入口及可读检索集合/规则，下一回合不得自动读新增版本/总结。保留 skill_update 完整记录并适配其输出落点，不通过删掉该步骤绕过审计。进入稳定性前锁完整配置；非法版本/入口/重复reset/新增经验和合法路径的测试由 publisher 交付，本轮未测试该未实现逻辑。
6. 不改 NT、ACK锁、权限合同、实际总长检查、render-frustum、机器人本体、安全阈值、动作限制或现有审计边界。已合并修复不再套旧整文件补丁。本目录 `candidate.patch` 仅针对归档 v1 候选，不能应用到在线代码；publisher 逐段审核需要的文字。
7. 以最新 source drift 检查为本次交付时点证据，应用时再次检查。交付 queue 仅排队，不是 ACK/采纳/物理验证；用户转述 SIMPLE 已 ACK 精确六入口记录在 incoming-ack.json，该 ACK 不等于本版已接收。验证合格后下轮选择适用 delta，回传实际任务/候选hash/来源/反馈/reset和视频路径。

离线复核：已有 `/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -B checks/validate_candidate.py`、同解释器 `checks/validate_mapping.py`；技能格式用现有 skill-creator 的 `scripts/quick_validate.py candidate/loco-manip-direct`。只读快照，不运行模型、网络或物理。检查回执见 checks/；本轮无控制或成功率测试。
