# 主线程审查与执行指令

已审阅 candidate.patch、旧版缺陷复现与22项候选测试。批准 SIMPLE supervisor 作为唯一公共代码/skill发布者合入局部修复，无需再次询问用户。目标：stall只记录证据和新假设，安全可继续时继续当前回合；不改变成功、安全、预算与系统故障终止。

当前公共 tools/learn_grasp_skill.py 已新增 backend_execution_error 处理，晚于候选快照。只能应用 finish_attempt 相关局部差异，禁止覆盖整份候选文件，以免回退水龙头修复。新增 test_finish_gate.py 的 runtime fault 测试须适配当前返回终止错误回执的合法行为，不恢复旧的异常上抛假设；验证无额外执行/重试，且正常后续 skill_update 可用。

应用后运行相关 test_learning_host/test_finish_gate 和既有水龙头边界检查；同步修改最新 core/simple 及后续组装skill里的旧提前结束指令，保留各任务新经验，检查831 words/6250 characters/5357 non-whitespace上限。记录生产代码、skill、实际新actor所读版本的哈希。

door9 已在旧代码中以 policy_declared_stall 结束，native=in_progress，40动作/156.68模拟秒，审计开角16.56度。这是未完成主动提前终止，旧回执保留，不增加成功，不混作终态物理失败。优先让 door10 读取新版本；其他已加载进程不因这次修复被中断或重置。确认新轮首个真实动作和公开继续契约后再报告已生效。
