# 继续 SIMPLE 主线，不能以启动或总结代替执行

最新分工优先读取 `ref/USER_UPDATE_20260916_SIMPLE_EVAL.md`。本 supervisor 与主线程后续专责 SIMPLE 测评、接收框架候选并反馈实测；旧段落的 IKEA 执行分工已被替代。与框架线程和地面搬运线程共享有证据的原子经验。自然边界消费 `artifacts/architecture-review-20260916/HANDOFF-SIMPLE.md`，先压缩入口再装实际总长检查，不能覆盖当前修复或热改在途回合。每轮更新 `artifacts/R019/PROGRESS.md` 和已有视频页，供主动进度通知使用。API 批准与“不查询额度”要求继续有效。

最新用户要求优先：先读 `ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md` 到文件末尾，后续旧文案不得覆盖它。不再查询API额度/余额/费率，不以计费研究阻塞已授权并行。优先核查并修复 `finish_attempt` 只需3动作即结束可继续回合的过宽规则；用户明确推门到门前未完成推动即退出属于未完成/提前终止，不是物理失败。当前在途回合不杀进程、不重置，完整等待；新代码生效边界要记录。苹果当前侧抓采用 `human-feedback/H001-user-feedback-004.json`：先同平面并确认苹果进入手掌包络，后闭合；不能以试闭合替代尚未满足的包络条件。先做已有失败的自主试验，至少3个可比探索仍不解才请用户看代表性视频。无需再澄清已回答的高度语义。

这是用户明确要求的连续执行，由零模型接续器在你上个进程自然结束后发送；不是新 campaign。先检查现有 tmux 和结果，接管而非重复启动。所有新模型调用仍通过第二账号 run.sh，gpt-6-astra/xhigh，保持工作区沙箱和自动审批。完整等待推理，不能用超时中断。若 usageLimitExceeded，停止模型重试，不消费重置券、不回退主账号/API。

先完整读取 AGENTS.md、ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md、ref/tasks/api-budget.json、artifacts/R020/supervisor-inbox.md（其中旧“预算未确认”已过时，以用户预算文件为准）、ITERATIONS.md 最新结论。明确确认已经读到这些新要求。主攻 SIMPLE 推门，独立真实成功至少10次；其他可用操作任务各至少1次，已有抓方块10次不重做。推门审计成功3次后与SIMPLE并行探索IKEA棕色带把手卧室门，资产/图片路径见用户更新文件。API预算全任务共享不超过10000元，每1500元报告；付费前核实来源/计费且验证共享原子费用预留。来源未明确只阻塞API分支，不阻塞SIMPLE。询问用户时把明确问题与当前图片路径保存到 human_observation_request.json，供桌面转达。

地面红块拾起并移动放到原桌面由另一个独立第二账号 supervisor 负责：thread 01a0a888-a98e-70d0-bd7a-0e268a6668ed，tmux rsi-ground-table-0916，写域 codex-account-2/workspace/ground-to-table。不要复制它的 campaign 或修改其写域。双方共享经证据验证的候选，不共享实时控制状态、tracker历史或物体真值。你是 skills/loco-manip-core/SKILL.md 的唯一共享发布者；先审查机制适用性/负迁移和回归，版本化后才晋升。独立角色/skill评审由 rsi-skill-review-0916 负责，复用 ref/ACCOUNT2_ROLE_SKILL_REVIEW.md 与 artifacts/R020/coordination-status.json，尚未存在就记录待交付，不重复研究。

推门优先完成能区分原因的控制诊断。运动学可达不等于动态可行，脚踝升高不等于整脚离地，不能因单个参考失败就宣布模型不能行走。新诊断先写假设、区分标准，再执行并记录证据与下一决定；避免不停改变小参数。正式actor保持四点ScaleBFM；VR-5/Full-14/直接关节PD仅诊断不计成绩。继续现有并行水龙头/苹果/抓盒等回合，审查其失败与skill更新，必要时利用用户的场景语义描述。保留视频与每次失败，模型暂停期间的物理不称RTC。

每次准备自然结束本管理回合时，在 codex-account-2/continuation/supervisor-state.json 写入：{"status":"continue|blocked|complete","reason":"具体原因","progress":"本轮新增事实","evidence":["证据路径"]}。只有所有原任务和用户新增范围实质完成才写complete；额度/必需外部信息等真实阻塞写blocked。仍可推进就写continue，接续器会在进程退出后再继续，禁止为了刷回合无变化返回。若同时有其他仿真仍推理，要完整等待或清楚交接，不能终止它们。接续器不会因你推理慢而重启你。
