# NT-AUDIT-20260916-v1：逐 turn 终态与审计兼容候选

**未部署。唯一接收/公共发布者为 SIMPLE 辅助 supervisor `01a0a867-d7aa-71f2-8547-e264d6d09ede`。** 本目录外未修改代码、技能、运行回合或旧评审结论。API/IKEA 是不同 Responses 调用链，不直接套用本补丁；本次不向其收件箱写入。

当前问题：旧 NT 自动恢复在 adapter 内吃掉 failed turn，caller 仅返回后写最终 `turn_002.json`，旧 auditor 只检查最后文件 completed，能把残缺序列当完整成功。
总目标：每个匹配服务端终态先保存，后续接；caller、adapter、auditor 使用同一显式完整性合同。
不可重犯的错误：不覆盖权限修复及并发源变更，不将未知请求/动作重发，不给残缺记录成功资格。

## 复现与接口

[复现](evidence/reproduction.log)将先前候选的网络处理部分移植到最新基线，保留当前 workspace-write/on-request/auto_review 权限及 ACK 锁。实际 run_episode 函数配假 transport/backend：t1 failed→t2 completed，只有 turn_002；`codex_turns=2`，旧 `episode_status` 却给 audited_task_success=true。两条正确性断言均失败。生成记录在 `evidence/reproduction-episode/`，仅离线夹具，不是物理成功。

只修改三个文件，见 [audit-compatible.patch](audit-compatible.patch)：

1. **adapter**：新增已接线的 `terminal_callback`。匹配 thread/turn 的终态在 return、raise、新 turn/start **之前**回调一次；记录 raw turn 不改其 id/status/error。ACK 后保存唯一 `turn_ids`，拒绝空/重复身份；callback 不存在则不启用网络自动恢复。网络分类复用旧候选，不重新实现已上线的 ACK 等待或权限合同。
2. **实际 caller**：`record_terminal` 使用唯一 `turn_NNN.json`、exclusive create、flush+fsync；不覆盖旧文件。raw turn 仍在顶层，新增 `_rsi_terminal` 的 contract、sequence、thread_id、recovery_reason、reset_id。原最后 completed-only 写入删除，避免双写。result 增加 `turn_record_contract='codex-terminal-sequence-v1'`、`codex_thread_id`、按 ACK 顺序排列的 `codex_turn_ids`，既有 codex_turns 保留。它们是本回合文件身份，不是新的任务成功系统。
3. **auditor**：新合同要求 ACK 数量/唯一身份、文件编号集合、每个身份/顺序/线程、每个终态一致；中间 failed 只有 host 标记的 `confirmed_closed_network_turn` 可经过，后续 reset 必须保持一致，最后必须 completed。无合同但有新 metadata 不降级旧格式。畸形/残缺 JSON、缺号、多号、错身份、未恢复失败或最后 incomplete 均不给完整成功。

恢复标签是**同进程 host 的控制决策**，auditor 检查标签与序列一致性，不把它当独立的物理任务成功或防恶意篡改签名。原来的 host success、actions>0、skill_updated、error-free、task success_review、completion_contract 与人工反馈分层仍是额外条件；memory_success_review 的现有入口读取这一结果，因此新序列缺失会取消成功优先资格，原生历史 outcome 与公开经验原文不改。未增加重复成功账本。

旧格式无恢复回合保留原口径；有历史 codex_turns 时额外拒绝已知编号缺口，无计数的旧格式仍只具有旧式末 turn 证明。旧记录不回填/伪装新合同；门16、水龙头8、苹果7原回执的全部既有审计字段与当前 auditor 一致。独立 reset 的原 host 审查职责未放宽，也没有从一个 reset 推导多次成功。

## 恢复边界及失败写盘

同一个 host 和 backend 对象、非空且相同的 `scene_setup.reset_provenance.reset_id`，已有新物理 action、没有 active 执行、host/backend 无终止/故障，且匹配的 `turn/completed(status=failed)` 是允许的网络错误，才续接。身份在工具回复写出后绑定；没有可靠身份则记录失败并停止自动恢复。reset 身份只用于 host 检查和终态文件，不发送给 actor。

错误通知、沉默、EOF、未知 ACK/reply 不产生恢复；quota/usageLimitExceeded/权限/安全/物理预算等保持终止边界。不把本地 reply 写出说成远端已收到，仍遵循已有观察/回执核对和禁止未知重放的合同。回调写盘或 fsync 抛错会直接阻止新 turn；caller 保存 error，auditor 不计成功。部分文件保留，不删除掩盖写盘失败。该写入不是主机崩溃一致性/快照恢复协议，目录项持久化也未被宣称具有断电保证。

无新物理进展的后续网络失败仍记录后抛错，现有 caller finally 关闭；**这个已知限制保留**，不声称维持了暂停的仿真现场。主机重启丢失的现场不能用本候选恢复。普通 completed 但任务未完仍沿用现有 caller 循环，没有新增任意次数/时间截止。

## 长度与应用顺序

完整安全/观察/不重放规则已在 pin 的 skill 与 immutable runtime 中；新续接提示有意只写 `Observe; next_call: `，后接现有公开 next_call 数据，没有截断任一 skill/推理文本。**预检和后续 skill_update 都预留这18个非空白字符**，使用既有 validate_policy_instructions/SkillMemory.runtime_instructions 检查三项上限。budget receipt 的 scope 明确包含 reserved network continuation，并另存真实 developerInstructions hash；task 数据/观测/tool schema 仍沿用既有分离口径。

六个实际入口+当前 runtime+恢复提示均通过 [长度检查](evidence/length-final.json)：最紧的是烤箱 800 words / 6172 characters / 5356 非空白，放盒819 / 6179 / 5346。因此每次采用/更新必须重做实际总长检查，不能再无条件追加说明。代码在创建 host/transport 之前预检，未来 revision 不能侵占预留。

发布步骤：

- 下一确认的自然边界再评审；不热改门17/苹果8/放盒4/烤箱1或任何后来启动的 actor。旧进程继续自己的已加载版本。
- 本补丁相对于 [patch-base-manifest.json](patch-base-manifest.json) 的最新基线；前两轮长度、审计检索、相机修复已上线，**不要重叠应用旧 combined/continuity 补丁**。使用本 targeted diff 的三个文件 hunk，不复制整个旧快照。
- 本轮两次发现 publisher 并发修改 auditor：新增任务映射/库存刷新、更新进度文案，均已保留。原/并发/最终快照分别保留；最终文案调整只改变 write_progress，已验证新审计/检索函数 AST 与63项测试版一致。最新零 fuzz dry-run 后的本地副本与候选一致，无在线写入。[漂移证据](evidence/drift-final.json)。
- 保留现有 workspace-write/on-request/auto_review 及 receipt 校验。原9项 adapter 回归包含权限拒绝测试；本轮没有另发握手/模型请求。
- publisher 按下面检查重跑后，在自然新 reset 采用。新回合标注新 turn_record_contract；旧运行回合不事后补写或改标签。真实网络恢复收益另由 publisher 记录视频/终态/是否退步，离线通过不代替物理验证。

复跑只使用已有解释器，不创建环境，所有临时文件在本目录：

```bash
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -B tests/test_joint.py
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -B tests/test_budget.py
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -B tests/run_regressions.py
```

18项联合、4项长度/更新、41项必要旧回归，共63项通过。旧回归包括9 adapter、12 LearningHost、2 campaign status、18 audit/memory。模块导入最初缺现有 locomanip/src 的搜索路径，失败日志保留；仅在测试进程 sys.path 补入既有只读源码，未安装/修改环境。测试中的 quota/写盘/EOF 字样均为故障注入，不是实际服务调用。

第一参考仍为已读 GPT-as-Policy 的同 context/rollout 与确认 closed turn 原则；不复制900秒、2次 continuation 或固定重试次数。公开原子经验材料已读，仍是任务条件候选：推门卸载不等于把手解锁，抓盒不等于持物行走/释放，放盒原生触发仍为反例；本次不编辑/晋升 shared core。来源hash见 [reference-hashes.json](reference-hashes.json)。
