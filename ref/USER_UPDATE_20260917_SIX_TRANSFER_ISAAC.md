# 固定主线：相似任务训练 → 六项 Isaac 测试

2026-09-17 用户明确纠正：

> 原有成功任务不再重试，只学习经验即可，不要浪费token，主线任务不再变化：改为在simple任务中选取与XMovePick、BendPick、Handover、Mobile P&P、Grasp、XMoveBendPick类似的任务进行训练，并以相同的setting在isaac中测试这六个任务。

本指令覆盖60×5/300回合、全部任务重复测评和成功任务复试要求。API授权与固定模型不变；旧计划回合仅安全收口，不续发请求。历史成功只提炼可迁移经验。训练任务与六项测试入口分开；具体精确入口与setting由现有版本及证据核实，不更换名称相近的任务凑数。测试版skill/harness在测试前冻结。Isaac渲染与Isaac物理执行分别标注，不以事后重渲染冒称Isaac测试。
