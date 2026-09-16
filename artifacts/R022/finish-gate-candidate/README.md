# R022 finish gate 候选（尚未应用）

触发：`finish_attempt` 在安全可继续、native=in_progress、有物理预算且已完成至少3次动作时，仅凭 stall/公共证据/新假设便结束回合。旧测试复现为3次动作后剩97步，却返回 `rollout_finished=True`。这是入口提前截断，不是已证明的物理失败；保留旧回执，不改成绩。

修复：保留工具名称、参数、动作数和公共证据校验。stall 只追加 `policy_stall.jsonl`，保留当前 `next_hypothesis`，返回当前 `observation_path`、`next_call` 和继续说明，不修改结束状态、不执行动作、不重置。后续真正结束时该日志可用于 skill 修订；旧 `policy_stop.json` 仍可被读取。工具说明同步修正。

生效边界：`candidate.patch` 只改工具文件、一个旧测试及新增回归文件。正常动作回执的 native 成功/失败、物理预算、初始化错误及运行异常处理原样保留；安全故障仍沿用现有 evaluator failure → native_failure，并未重构终态分类。补丁不保证任务成功，也不把 stall 诊断算物理尝试。

**由主线程审查后指令唯一 owner（SIMPLE supervisor）应用。本候选未应用到共享树，不会修复当前已加载进程；需要后续新启动进程读取新代码及配套 skill。** 本任务未运行仿真、模型、付费 API，未查询额度或修改环境/在途进程。

交付与验证：

- `candidate.patch`：三个文件，已在 `review-apply/` 检查并应用，结果与 `candidate/` 逐字一致。
- `logs/02-baseline-red.log`：旧实现目标断言失败，exit=1；`03-candidate-green.log`：同一复现测试及相关测试，共22项通过，exit=0。
- 继续动作、重复诊断保留、禁止提前 skill_update、成功/安全终止、预算耗尽、系统异常不重试和初始化错误均有检查。后端为单元测试替身，无真实物理成绩或视频。
- `logs/01-baseline-red.log` 保留首次导入路径错误，不能算缺陷复现；只增加命令级既有源码路径后重跑。
- `SKILL_CHANGE_SUGGESTION.md`：core/simple 旧段精确替换建议，检查全部长度上限；共享 skill 未修改。
- `baseline/` 保存原实现，`candidate/` 保存通过测试的副本；`source-manifest.json`、`DECISIONS.md`、`verification.json` 保留版本、来源、决策及核验。
- 并行过程中共享 SIMPLE skill 更新，但83个共享 Python 文件未变。两个 skill 快照均保留，旧结束段在新版本仍未变；owner 应替换最新版本该段、保留新增经验。首次漂移断言及后续核验见 `logs/04-review-checks-attempt1.log`、`05-review-checks.log`。

复现命令（只读既有解释器/依赖；两个目录的 tests/ 仅含相关测试）：

```bash
cd /home/galbot/lizekai/RSI/artifacts/R022/finish-gate-candidate
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/tmp"
export PYTHONPATH=/home/galbot/lizekai/Loco_manip/locomanip/src
cd baseline
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -m unittest discover -s tests -p test_finish_gate.py -k test_stall_keeps_safe_attempt_open_and_next_hypothesis_is_testable -v
# 上述应失败；继续到隔离候选检查。
cd ../candidate
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python -m unittest discover -s tests -v
```
