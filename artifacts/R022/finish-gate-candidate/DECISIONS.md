# 决策记录（公开工程判断）

## D01：隔离快照与先失败复现
当前问题：finish_attempt 在 native=in_progress、仍可继续且有预算时仅因 stall 结束；旧测试锁定该行为。
总目标：制作未应用的最小补丁，先复现失败，再验证继续执行及已有终止通道。
不可重犯：提前结束不得称物理失败；不写共享 rsi/tools/tests/skills；不启动仿真/模型/API，不打断在途；不读凭据/额度，不改环境。
决定：复制当前相关 Python 源码和原测试进 baseline/ 与 candidate/，保留 SHA256；在 baseline 上只新增复现测试。单元测试后端为测试替身，不计真实动作/成功/失败。
来源：AGENTS.md；/home/galbot/AGENTS.md；ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md；ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md 末尾；用户本轮任务。
模型约束：gpt-6-astra/xhigh；若需新模型只能 codex-account-2/run.sh；本任务不启动任何模型进程。

## D02：修正隔离测试的导入路径
当前问题：首次 baseline 测试导入失败（缺 locomanip），未触达 finish gate，不能算复现成功。
总目标：在原代码上得到明确的 rollout_finished 断言失败，然后只修复候选代码。
不可重犯：不安装/修改环境，不把 ImportError 充作 bug 证据，不隐藏首次失败日志。
决定：只读定位已有 locomanip 源目录，使用本次命令 PYTHONPATH；保留 01 日志并用新的日志序号运行。

## D03：只将 stall 请求降为回合内诊断
当前问题：02-baseline-red.log 已在旧实现上得到目标断言失败：第3次动作后97步剩余、native=in_progress，finish_attempt 返回 rollout_finished=True。
总目标：保持原工具参数和 >=3 完成动作/公共证据校验，阻止停滞误触发结束，并能继续验证当前 next_hypothesis。
不可重犯：不引入门资产/隐藏接触/物体真值规则，不重置，不覆盖旧证据，不改正常成功/安全故障/预算/系统异常通道。
决定：候选删除 stall 的 self.finished/stop_reason 赋值；追加 policy_stall.jsonl，返回 observation_path、next_call 和继续说明；终态 evidence 清单兼容旧 policy_stop 并纳入 stall 日志；仅更新旧行为测试，新增有意义的继续/终止回归。共享 skill 仅交付精确替换建议。

## D04：封存候选并交接唯一 owner
当前问题：隔离候选的22项相关测试已通过；需要可应用的补丁和精确、不过长的 skill 建议。
总目标：交付 candidate.patch、简短 README、先失败后通过日志及来源记录，供 SIMPLE supervisor 审查。
不可重犯：不将候选应用到共享代码，不修改正在加载的进程/skill，不覆写旧结果，不以替身测试冒称真实物理验证；仅检查改动相关内容。
决定：补丁仅包含 tools/learn_grasp_skill.py、tests/test_learning_host.py、新增 tests/test_finish_gate.py；在独立 review-apply/ 做补丁适用性检查，检查源文件漂移及建议文本长度；不重跑已通过的测试或扩大全量。

## D05：保留并行 skill 漂移，不强行覆盖
当前问题：候选补丁在 review-apply/ 的检查与应用均 exit=0，3文件逐字匹配；随后来源检查发现共享 skills/loco-manip-simple/SKILL.md 自快照后变化，断言未通过，检查脚本在写汇总日志前退出。
总目标：如实记录漂移并交付可审查候选；共享发布权仍属 SIMPLE supervisor。
不可重犯：不得把别的进程新版本覆盖回快照，不隐瞒审查失败，不把已在隔离目录应用误称共享已应用。
决定：保存此审查回执摘要；只读新 skill 并另存后续快照，建议明确适用版本；只继续剩余核验，不重复测试或重做已经通过的 patch round-trip。

D05结果：共享83个 Python 文件未变，新增测试不在共享树；SIMPLE 新经验段更新，但待替换的旧结束段逐字未变。两个版本的 skill 替换建议均满足全部长度上限。补丁/测试不需变化，保留首次审查断言及漂移记录；05-review-checks.log 完成剩余核验。
