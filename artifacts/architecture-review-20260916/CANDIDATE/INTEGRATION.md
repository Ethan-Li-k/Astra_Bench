# 候选v1：合并指令长度检查，未部署

归属：SIMPLE supervisor唯一发布共享技能；API工程师只维护其独立副本。本目录不是运行时输入，不自动触发任何模型/物理回合。

包含两个源文件的最小补丁和一个短技能入口，属于同一个长度合同修复：

- `rsi/skill_learning.py`：复用skill_size，检查skill+runtime总长；自动skill_update在任何写入前检查，read返回占用值。原证据/版本/失败流程保留。
- `tools/learn_grasp_skill.py`：只把原runtime字符串移到函数开始；在episode创建、host和transport前校验，绑定本回合runtime预算。原运行合同内容及已有终止/异常逻辑不变。
- `loco-manip-direct/SKILL.md`：短入口，具体任务及数值经验仍读workspace/task_specification、experience_read和已列公共来源；未引用host审计文件、隐藏接触/状态/奖励。不是直接用作新任务定义。

顺序：

1. 让当前推理/回合自然结束。对目标代码核对manifest内baseline hash；不一致时逐hunk整合，禁止整文件替换。不要触碰API独立工程师在途修改。
2. 保留现有task skill和完整memory版本。短入口需连同该任务已有workspace/source registry评审；特别保留已批准的人类反馈及任务终态合同。详细数值经验不删，继续按需检索。
3. 对所有将调用同一runner的新回合技能校验**skill+原runtime**（831 words、6250 characters、5357非空白），再合入补丁。只装补丁而保留超长入口会拒绝启动；应当在发布前解决，不绕过检查。这个限额对象是主actor developer指令；任务数据、工具schema、观测和按需经验不是此检查的对象，不宣称整个上下文只有此长度。
4. 离线跑 `PYTHONDONTWRITEBYTECODE=1 python checks/test_candidate.py`；8项覆盖原bug、三类边界、启动前无副作用、更新失败不写、有效版本/来源保留。AST仅提取真实runner函数以避开物理库初始化；这不是完整runner/模拟集成测试。
5. 发布者授权的新回合才做物理回归：匹配controller/reset setting，比对旧/短入口的有效动作、成功/提前结束/预算及调用成本。候选目前只有离线正确性，不能宣称物理不退化或泛化提高。

已保留baseline与unified patch。无live文件已应用。系统python缺PyYAML的首次技能校验失败日志保留；改用既有只读 `locomanip_sim/bin/python` 后官方quick_validate通过，未安装依赖或创建环境。

事实来源：当前三个skill及caller；GPT-as-Policy短入口/context合同写法；door0011公共stall与动作19；grasp437/438公共经验；BendPick0006公开决策；苹果H001-004为显式给定时才用的条件反馈。源hash见上级source-manifest，候选hash见manifest.json。未经独立物理验证的规则保持候选；失败反例未删除。
