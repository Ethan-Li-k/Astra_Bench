# SIX-TASK-FOCUS-V1：应用边界

唯一集成人：SIMPLE publisher `01a0a867-d7aa-71f2-8547-e264d6d09ede`。本目录候选未部署，不启动或接管campaign；IKEA/地面维持用户暂停，旧接续与接管请求不再执行。

1. 保留当前正在运行的 BendPickSim2、XMoveBendPick3、MobileCheezit1 冻结入口，等待自然边界。先阅读原轨迹/审计/版本，再决定是否需要摘用模板的阶段改进。已达标XMovePick/BendPick不为凑数重开。
2. 仅把 `candidate/loco-manip-direct/SKILL.md` 和**一个** `candidate/deltas/<family>.md` 用一个换行连接成下一任务的入口，或把所需最小段落合并到已学会的当前入口。不是安装新全局skill，也不是覆盖共享core。若摘取/继续追加旧经验，必须重测最终实际入口；本次六组合的通过不覆盖任意拼接。
3. 沿用 `prepare_hybrid_skill` / `reviewed-task-sources.json` 和现有 workspace allowlist。按[experience-map.json](experience-map.json)选少量匹配公开版本及其rollout；不要复制本目录 REVIEW、原生准则、success_review、pause-evidence 或host接触/奖励文件进actor。目录“来源”不等于全目录访问权；数值配方仍留在可选择的历史公共版本。H001004衍生来源保持人工语义反馈层，未读来源不伪造选择记录。
4. 使用现有 `validate_policy_instructions(final_markdown, immutable + NETWORK_CONTINUATION)`，且仍给 `SkillMemory.runtime_instructions` 同一预留。现快照overhead=266words/1982chars/1715非空白，hash见checks。全部六组合≤716words/5333chars/4613非空白，frontmatter也通过既有validator；保留旧版，不裁断推理或文本凑长度。没有修改caller/harness、NT逐turn持久化、权限合同、render-frustum、机器人本体字段、故障原子性或安全阈值。
5. 新回合pin任务/接口/skill/controller/seed/feedback/contract版本，使用原物理预算。技能修订仍由原流程在真实事件后保存；不把本离线模板写成已学习的成功经验。Grasp入口待用户澄清；Handover在选定变体后先固定完整移交审计方案。
6. 成功排序保持现行 memory-priority：只有完整且独立审计通过、合同匹配的来源才置顶。失败/否决/未知/变约定保留原始 outcome，仍可作为反例或最近记录。host callback选择合法公共记录/传已有布尔标签与暴露原审计payload是两件事；只允许前者。不要重复套旧combined-compatible整文件补丁，已修功能继续保留。
7. 事件触发review：完整新回合、任务合同改变、实际重现错误或明确人工纠正。反馈选用来源、适用性变化、公开反例和实际新版本；工程ACK、采用、物理验证分别记。没有独立A/B不将并变成功归因模板或本体字段。

复现本次离线校验（不运行模型/物理）：用已有 `/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -B checks/validate_candidate.py`；快照保证可重现当时结果。实际应用前对最新caller重新提取固定文本并检查源漂移。`collect_evidence.py`与`build_review_sources.py`是本次一次性证据抽取，不是新定时器。暂停脚本是已执行的一次性授权动作，不可再次运行或作为自动接续/关停服务。
