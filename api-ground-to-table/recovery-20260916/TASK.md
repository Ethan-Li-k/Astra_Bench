# 主机重启后的物块搬运恢复（辅助账号唯一执行者）

用户最新要求：“继续推进，并且在网页端给出进度”。持续任务范围见 ../CONTINUATION-20260916.md；本分支只负责原桌位地面红块的 locomotion→grasp→loaded locomotion→table placement。所有模型仅本辅助账号或既有授权API，gpt-6-astra/xhigh。禁止主账号、额外子代理、余额/配额/费率查询、环境修改或真机。三行决策；代码apply_patch，长任务tmux+tee。不读取认证内容进上下文；API凭据仅既有transport内部使用。所有产物RSI。

## 已确认的新事实（不要再当作在途长推理）

父任务在宿主权限下核查：uptime -s 返回2026-09-16 02:08:07（America/Los_Angeles）。原API PID3537389、辅助工程PID3431415均不存在，原tmux rsi-api-ground-002-0916/rsi-aux-api-002-0916不存在。这是主机重启，不能归因于模型慢。原公开进度停在02:07:38：api-ground-002/episode-0002，54个完成调用、23动作、108.98物理秒，仍无终态/抓持成功。第55次 api_calls/55/receipt.json 和 artifacts/R021/api-ground-002/api-ground-002-call-55-plan.json 均为0字节，run-002.log末尾有NUL；ledger79921字节。未知请求费用不得清零，不能假定55未发出，也不得自动重发。

UI服务已由另一owner重启，当前human-feedback/dashboard-upgrade任务正在升级四任务页面，tmux rsi-dashboard-upgrade-0916。你不改UI/server、不重启其进程。框架owner正在 artifacts/architecture-review-20260916/no-truncation 做连续性审查，tmux rsi-continuity-review-0916。不要与其抢写域或覆写live shared core。原API工程师的工作文件、所有旧证据保留。

## 按顺序推进

1. 完整读取当前AGENTS，以及 ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md、HUMAN_FEEDBACK.md、NO_TRUNCATION_SHARED_SKILLS.md。参考已有研究，GPT-as-Policy优先、RoboRSI次之。需要改skill/API实现时读取适用系统skills并按指示使用，不重新调查价格。新辅助身份必须记录。
2. 先留下重启/缺失进程/最后ACK/调用与轨迹完整性证据，不修改原回合/原receipt/原ledger来填造正常结果。核查真实最后完整动作、公开观测、55的账本行与空文件，保留原状态快照。根因主机重启与具体磁盘损坏程度分开表述。未封口视频只做只读ffprobe检查，不改写原视频，不称完整。必要恢复副本单独留名，无法恢复就明确。
3. 立即将本分支可变的 actor-adapter/auxiliary-progress.json/status.json 更新为真实 infrastructure_error/recovery 状态，保留上次物理数字和时间，加非猜测的重启原因、当前恢复owner、最新更新时间。旧快照版本保存到本recovery目录；不要把刷新时间写成新物理进展。网页只投影公开字段，联系UIowner接入恢复说明，禁止host真值进入网页/actor。写本目录progress.json和RECOVERY.md，让用户能看到不是仍在旧推理。
4. 恢复同物理回合仅当完整sim/controller/history状态确实存在且可校验；只有命名机器人观测/动作日志不够。不能补造“原回合无缝恢复”，不能重放旧动作冒充学习。若状态已丢失，将旧回合标为infrastructure interruption（追加独立审计记录，不覆盖原始记录、不计失败求助），提炼公开条件化反例，准备一次全新独立尝试。用户继续推进授权任务内后续尝试，但不允许重试55、不超原共享10000元/1500报告、原公开资料发送范围、单批120请求/原180秒物理、安全阈值、原setting。续批需要新的可核验run/episode/auth/批准记录和正常执行审批，不得把旧单episode批准冒用给新episode；如果工具审批/账本权限不能满足，保留进度并明确上报，不绕过。
5. 费用恢复只用本地真实回执、账本和重启证据，不查询quota或追问价格。先检查ledger哈希/引用/0字节损坏；未知费用继续占用预留。若明确授权的续批需要区分“旧调用已完成但费用未知”和“重启后结果未知且绝不重发”，最小改动需先写复现/非法输入测试；不能伪造completion或释放旧hold，不能放开未知其他任务请求。正常reserve/begin/once-only规则保持。不在未完成审核时发模型请求。
6. 新回合前读取可用SIMPLE公开候选及框架交接（HANDOFF-API、memory-priority、no-truncation）；兼容性过滤后记录用/不用的原子skill、控制器/合同hash、前提、失败反例及本轮不同检验。首批/本次接近扭转和支撑退步只是候选，不宣称步态掌握。同一失败动作不要盲目重复；不能把23动作凑成3独立失败。保持原始G1/DEX3/model38000/WristPI/原table0，禁止改成功定义或放宽控制安全线。
7. 最小修复验证后启动独立tmux+tee新物理进程，只用直接API，无主账号/CLI fallback。不因推理等待设置超时或重发。若出现模型自然无工具turn但物理未结束，按已核验连续性合同接续；不凭任意for-loop自然退出。仍保留真实预算/安全/系统停止分类。每回合完整保存公开证据、终态、视频与经验，正常边界后按最新用户要求继续任务内有区分力的尝试，不自动换任务到SIMPLE/IKEA。
8. 三方协作仅辅助queue/现有inbox，不唤醒主账号。已知框架辅助thread01a0a94d-6143-74c0-80cd-03d0b61acaf0；UI升级的实际新辅助thread从其已存在启动回执读取，再queue一次恢复身份/网页字段索引；SIMPLE用 artifacts/R020/supervisor-inbox.md追加带hash消息。旧ground辅助thread01a0a948-10bb-7d03-8f1d-b1eeda7cb93c已随重启消失，不并发resume，不声称旧queue已消费。明确新owner和消费旧待办的ACK，防网页将新反馈继续只发给旧owner。

验收：网页能看到真实中断与恢复/新回合进度；无旧请求重发/原证据覆盖/主账号fallback；恢复诊断有证据，新尝试有独立重置与skill来源，当前真实backend标注；所有测试/启动或阻塞在本目录记录。完成有意义阶段再公开报告，不逐API调用播报。真实授权/系统阻塞不能用用户“不停止”绕过，立刻在网页/RECOVERY.md写清需要的决定。
