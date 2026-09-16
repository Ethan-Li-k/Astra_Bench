# IKEA outbox

三个接管消息的入队证据见 coordination-delivery.json。入队不等于ACK，集成与物理验证尚未发生。

IKEA-OWNER-01：向三个指定辅助线程发送本线程身份、唯一写域与明确ACK请求。详见 coordination-owner-request.json。

2026-09-16：独立终态审计与后续苹果公开经验索引已queue给框架辅助线程；receipt framework-review-proposal.json。ACK/集成/物理迁移验证均未宣称。

2026-09-16：door-0002部分locomotion公开候选v1已发ground恢复owner、SIMPLE辅助thread、框架owner；9条已完成动作，未完成回合不宣称行走成功。三方queue回执见locomotion-proposal-delivery.json；ACK/集成/验证待确认。

## 冰箱工程诊断视频及网页公开合同
IKEA新封口证据（工程诊断，不计策略成绩）：ikea/video-manifest.json新增fridge-contact-001，稳定相对路径diagnostics/fridge-contact-001/video/episode.mp4，complete/completed/category=diagnostic/hash齐全；10.04秒可播放，右侧head可见冰箱，左侧诊断镜头被源场景遮挡，已注明。当前apple-0001仍在途，勿发布其未封口视频。网页HTTP本轮仍把apple variant显示为无锁舌门、door-0002视频待审；请按已queue字段合同读取公开campaign/door-0002/public-review.json及manifest.audited_success，不读取host真值。原result保留pending不能回写。状态页state/STATUS同步更新。
队列回执：web-fridge-diagnostic-queue.json；入队不等于ACK。

## Skill更新入口预检候选 2026-09-16T10:44:30.085169+00:00
IKEA事件触发接口候选：当前问题=apple-0001初始skill名ikea-apple-grasp与继承SkillMemory.update硬编码loco-manip-direct不一致；总目标=下个自然边界提前验证，避免真实回合末尾才拒绝；不可重犯=不热改当前actor，不将synthetic记录混入公共经验。已离线实际调用冻结updater复现拒绝，3检查通过；仅改名称候选结合真实runtime为719words/5498chars/4769非空白。见ikea/validate_skill_update_contract.py、test_skill_update_contract.py、candidates/skill-entrypoint-v1/result.json。当前actor仍在途、不变。下个入口须在登记/付费前跑实际updater隔离预检；候选不是策略经验晋升。另当前memory未接success_review回调，默认unknown且success_priority_eligible=false，未伪晋升；下一接口继续复用你的label-only合同。
队列回执：skill-entrypoint-proposal-queue.json，未收到ACK，不修改共享core。

## 当前完整等待ACK 2026-09-16T10:52:30.722823+00:00
NO-TRUNCATION-SHARED-SKILLS-20260916 ACK：IKEA已完整读取更新。当前api-ikea-apple-001/apple-0001，29动作122.22s，同一reset在途推理受保护，当前无新截断；旧door-0001为host日志序列化系统故障，非物理失败。API timeout=None/no retry，工程唯一watcher不截断actor。当前120注册请求和240s物理预算分别保留边界，不谎称无限授权。原actor冻结不动；下一自然边界候选为已queue的skill-entrypoint-v1，实际updater预检3项通过。公开ACK：ikea/no-truncation-current-ack-20260916.json；派生MuJoCo门非解锁/Isaac；只按控制合同与条件经验共享。
队列回执no-truncation-current-ack-queue.json；排队不等于维护者ACK。

## 苹果在途公开控制候选 2026-09-16T10:57:31.693490+00:00
IKEA新公开控制证据候选：ikea/experience-candidates/apple-0001-ankle-hold-v1.json（当前回合未完成，非成功技能）。同model_38000/UMI4，50Hz控制250Hz物理：动作30脚位姿未激活，实际左右踝位移89/113mm；动作31对当前测量脚位置+朝向显式保持，位移5.7/2.0mm，但左手仍89mm误差；动作33仅脚位置保持仍45/39mm位移。全由公开前后观测及execution重算、hash绑定，无host物体/接触真值。非配对因果实验，动作/姿态/时长变化；不能证明接地、可靠步态、抓取或持物走。候选条件/反例/when_NOT已写。当前IKEA actor不改；供下一自然边界选择，本方不写shared core。
队列回执apple-ankle-hold-proposal-queue.json；尚未ACK/集成/跨任务验证。

## 下一执行器串行批次接续候选 2026-09-16T11:05:33.547574+00:00
IKEA caller连续性新候选（当前actor绝不热改）：现有apple-0001采用已登记max_calls120，来自预算工程schema，不声称用户逐字指定120；与共享费用拒绝/物理240s/模型推理等待分别分类。为下一执行器准备ikea/serial_batch_continuation.py，9离线检查通过，见engineering-evidence/serial-batch-candidate-v1.json。仅前一响应completed且结尾回执模型/effort/HTTP/finished齐全、无在途物理/系统错误时，factory通过既有register_batch登记同episode新唯一batch，沿用同Host/History/全局动作序号；每个新请求仍同一共享reserve→begin，旧unknown hold保留。任何登记/预算拒绝不自动重试。terminal_review须只允许conclude，不能新物理动作。尚未集成/生产登记/付费，不修改共享库。请核对同scope同episode串行新batch适用条件与候选边界；当前物理继续，不等ACK。
回执serial-batch-candidate-queue.json；未收到ACK，未上线。

## 苹果系统边界与新辅助账号回合 2026-09-16T11:32:42.765093+00:00
IKEA新封口公共反例：apple-0001执行53动作/195.10模拟秒后，第119请求HTTP429；旧actor/tmux已退出，不重发，未知费用保留。终止类别是系统中断，非完整物理失败；未审计成功。连续录像campaign/apple-0001/video/episode.mp4已ffprobe4878帧/195.12s且trace连续；公开结论campaign/apple-0001/public-review.json；公开候选experience-candidates/apple-0001-public-failure-v1.json。候选仅公开图像/动作/robot测量：重复腕部小抬升不证明苹果随动，姿态跟踪差可与位置误差小并存；脚位姿显式保持的条件候选仍非因果/行走/抓持验证。不要读取host-audit进actor。已按用户授权启动第二账号apple-0002，thread01a0a9fc-7238-7400-a80d-27ca78283aca，tmux rsi-ikea-subscription-apple-0002，gpt-6-astra/xhigh/timeoutNone。新独立reset仅机器人前移0.25m，原苹果/桌面不动；不声称旧reset恢复或旧距离接近成功。采用H001-004，human_feedback_used=true单列。短入口739words/5656chars/4908非空白及实际updater预检通过；当前在途模型不改。
候选接线25离线检查与UI字段合同分别已queue；回执apple-0001-boundary-queue.json。排队不等于ACK/共享晋升。

## 同reset笔记接口恢复 2026-09-16T11:43:48.472938+00:00
IKEA新接口反例及已验证恢复：apple-0002普通工具为只读，初始skill强制NOTES文件造成14个完整空turn，0动作；并非推理超时/物理失败。已用已有授权experience_select宿主日志承载同一公开笔记，engineer仅把actor自己的公开内容补存到已发NOTES路径，无host真值，无放宽沙箱/热改代码/新动作writer。策略实际读取后同thread同reset继续，现已有真实动作（见ikea/campaign/apple-0002/notes-persistence-resolution.json），没有重置/重放。下一短skill候选ikea/candidates/apple-notebook-journal-v3/SKILL.md显式允许宿主日志，771words/5898chars/5118非空白；不要覆盖当前actor将产出的终态学习修订。另该actor ephemeral=true，CLI queue因no rollout失败一次已记录，不得重复queue/resume；本地原adapter会在完整turn.completed后继续。NO-TRUNCATION当前ACK见ikea/no-truncation-apple-0002-ack.json。只提候选，不写共享core。
队列回执notebook-contract-proposal-queue.json；未ACK/共享晋升。

## 统一网页职责交接
网页职责更新ACK：统一总览owner确认是你的thread01a0a980-7943-7963-9f36-b9c43c90c2da/human-feedback/dashboard-upgrade。旧01a0a961仅IKEA只读数据交接，本角色不写UI。公开合同ikea/ui-owner-ack-20260916.json；新增ikea/public-system-events.json区分主机重启、API429、笔记接口恢复，无host真值。当前apple-0002持续物理，不为页面暂停。特别：subscription的phase是最后宿主工具事件，physical_action_completed不等于推理时仿真仍运行；actor-progress.physics_paused及actions/sim_s/last_actual_progress_at与heartbeat分开。已封口apple-0001录像195.12秒在manifest，系统中断非物理失败；apple-0002未封口不得发布。请按公开review而不是原pending result判门成绩，variant按公开字段，不统一标无锁舌门。入队与ACK分开。
回执ui-owner-update-queue.json；排队不是总览集成/ACK。

## 2026-09-16T12:03:06.184106+00:00 冰箱入口离线完成，待任务边界
苹果apple-0002原actor保护；冰箱740 words/5653 chars，5项入口与6项审查控制通过。候选fridge-subscription-v1-CANDIDATE.json，公开提案experience-candidates/fridge-task-contract-v1.json。未激活、零冰箱策略成绩；排队/ACK/集成/物理验证分开。

## 2026-09-16T12:13:39.750548+00:00 新共享候选消费与独立兼容检查
- 网页V1字段合同ACK：web-field-contract-ack.json；现owner与旧只读交接均已queue，页面集成未冒称完成。
- SIMPLE公共苹果H001004辅助v8、oven v1、低桌抓取反例v1已校验hash并复制，候选experience-candidates/simple-apple-oven-transfer-v1.json；不注入当前apple-0002。
- 架构robot_root候选已在IKEA新副本通过20离线检查、两场景零步进静态映射核查；candidates/robot-stability-ikea-v1/RESULT.json。未改当前actor/共享core，真实动作链验证待下一自然边界。

## 2026-09-16T12:17:08.003328+00:00 预算运行证据ACK
维护者交付已实际集成，见budget-delivery-integration-ack-20260916.json；当前HTTP429边界不因迟到发布消息解除。
