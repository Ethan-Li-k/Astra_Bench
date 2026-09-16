status=applied_no_live_process_modified

已完成一次性、三文件局部整合，完成即交回 SIMPLE supervisor。finish_attempt 的临时 stall 现在只追加诊断并继续本安全可执行回合；保留已有 backend_execution_error 捕获。原成功/安全/物理预算/系统故障终止路径逐字未改。

23 项定向测试一次通过（test_learning_host 10、test_finish_gate 5、test_continuous_control 3、test_reference_sequence 5），exit=0。使用 candidate README 指定的既有解释器 `/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python`，由专用 tmux + tee 运行；临时文件只落本目录。后端为单元测试替身及纯数值检查，物理尝试/成功均为0。

可核实材料：

- [production 应用补丁](production.patch)
- [完整回执与逐文件哈希](status.json)
- [初读/备份前哈希](before-sha256.json)、[应用前再次核对](preapply-sha256.json)、[应用后哈希](after-sha256.json)
- [实际测试日志](logs/04-tests.log)、[测试结果及测试期间源码哈希](test-results.json)、[测试命令](run-tests.sh)
- [最终内容与 patch 检查](logs/05-final-verification.log)、[决策记录](DECISIONS.md)

before/after SHA256（新文件原先不存在，无 before 内容哈希）：

- `tools/learn_grasp_skill.py`
  - before: `aa24ab3daba4c323707cf3ba9749aa47ea771ef2ac2c45235efa0faa5438b801`
  - after: `469137e005112b59ce92075aac63281635047f636002ef8b774cbea78ea17b11`

- `tests/test_learning_host.py`
  - before: `27b34dbb3803e83af211c81c48673a70a0c8f69051a563bcea370dfca93b7270`
  - after: `00733a8d5c17bb4da9b14ffd660bfe80679eebdc8082a4340960a836ded0e3bc`

- `tests/test_finish_gate.py`
  - before: `ABSENT (new file)`
  - after: `5e567a461e3d4f49da4c98b3667a0610c22229636d60cc4d700aa5dda10a5609`

给下一新 actor 的契约：

1. 新进程核对并加载上列生产工具哈希；本次没有启动新 actor，也未验证任何在途 actor 已采用新版本。
2. >=3 次已完成动作、无活动动作且当前公开证据合法时，finish_attempt 追加 policy_stall.jsonl，返回 rollout_finished=false、observation_path、next_hypothesis、next_call；不执行物理、不重置、不结束回合。依据当前观测在本回合安全检验新假设，避免原样重试和 idle hold。
3. 仅真实终止回执 rollout_finished=true 后提交 skill_update；原 native 成功/失败、预算、初始化错误和运行错误终止保留。RuntimeError 返回 backend_execution_error，finished=true、retryable=false，不重试，仍可正常 skill_update。
4. skill 同步由 SIMPLE supervisor 负责。精确旧段替换已列于 [SKILL_CHANGE_SUGGESTION.md](../finish-gate-candidate/SKILL_CHANGE_SUGGESTION.md)，本次未修改该文件或任何 skill。owner 应保留最新经验并核对实际组装 skill 与长度上限。
5. 已运行 door10 未热修；不得把这里的单元测试日志当物理结果或线上新版本采用证据。

整合过程：第一次 patch dry-run 因补丁上下文空格缺失失败，生产未改；修正一个格式空格后预检通过，再次核对全部三文件状态并应用。所有生产源码修改均为局部 hunks，未覆盖整文件、复制 baseline/candidate 树或回退并发内容。初读至应用前未检测到并发漂移。两次沙箱 tmux socket 拒绝发生于测试启动前；自动审批后仅启动本目录专用单测会话，实际测试执行一次。
