执行一个有边界的独立物理复现任务：SIMPLE苹果episode0003动作59后闭合/抬腕失败。使用第二账号gpt-6-astra/xhigh；不调用付费API、不读凭据、不新建子agent、不改环境/原资产/公共rsi和tools/skills文件。超过60秒命令tmux+tee。先读AGENTS.md、ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md及human-feedback/cases/H001/case.json、H001-user-feedback-001/002.json。

唯一写域 human-feedback/reproductions/H001/。该目录归你独占；SIMPLE supervisor继续推门和其他正式任务，UI线程只负责human-feedback/tools/ui/annotations及表单。不要重复启动任何campaign。

目标不是新任务成功，而是证据充分的真实动力学失败复现。原episode位于 artifacts/R019/apple-campaign/episode-0003。用户指出手掌高于苹果、拇指不可见，预测闭合抓空；优先下降，达到同一平面再闭合。此处参照部位仍在澄清，不能自行将掌心等同指腹，也不能提前宣布用户根因已证实。

先核对原始task spec/seed/reset状态/模型38000及控制参数/关节名顺序/源版本、原始动作序列、tracker历史与采样时序；查看现有tools/replay_direct_episode.py能否复用，但禁止改公共工具。使用已有SIMPLE解释器和环境，原资产只读。优先从同一原始reset完整执行旧动作前缀至动作65，保留物理及tracker历史，不直接teleport到第59帧仅设置qpos冒称完全同状态。可在你的目录写独立复现脚本，重用现有SIMPLE环境/接口；不输入用户反馈到原动作基线，不新建GPT actor。

如原runtime有历史快照，优先隔离恢复；没有则先记录代码/资产/初态差异，利用兼容接口做明确标注的复现对照。对比初态及选定时间点命名本体/物体状态和轨迹、图像、控制目标，host差异审计只保存在host_audit/，不能写入公共反馈或策略输入。阈值必须先明确并报告，不能看到结果再放宽。存在实质性发散时停止因果归因，保存最早偏离位置和原因候选，不宣称同条件。

实际执行后保留原动作→新物理记录→视频/关键原相机图→差异审计→简短复现结论。视频回放/渲染不是新物理；所有结果 task_success_credit=false、reproduction_only=true。若原问题复现，冻结 baseline，再输出可供下一阶段的单变量修正实验说明：仅修改进入闭合前的高度判断/下降阶段，保持其他尽量一致，策略只能得到RGB/本体/用户语义反馈。**本有边界任务先不运行纠正actor**，待用户平面参照澄清后交给主控或新授权续接，避免未经确认改写规则。

写 human-feedback/reproductions/H001/status.json 和 REPORT.md，包含phase、真实命令/日志/视频、复现匹配度、是否观察到失败及证据、未确定根因、下一实验、不计成功。不能因复现困难停在计划；用已有环境完成能做的检查及至少一次可信的真实复现尝试，除非有具体阻塞。结束后通知桌面，主任务持续运行。
