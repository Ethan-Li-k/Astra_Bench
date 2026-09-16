# SIMPLE 主控接续检查点（2026-09-16，本次控制/碰撞修复后）

先重读 AGENTS.md、USER_UPDATE_20260916_PARALLEL_SKILLS.md、USER_UPDATE_20260916_HUMAN_FEEDBACK.md、api-budget、R020 inbox和ITERATIONS末尾，检查tmux及最新result，接管而非重复启动。套餐模型固定第二账号run.sh、gpt-6-astra/xhigh；不截断推理、不建通用代理/新watcher，不读api.json/auth.json。最新API分支授权见HUMAN_FEEDBACK用户更新，禁止再调查额度/余额/费率；本主控未新建付费调用。代码/日志/缓存统一RSI，不修改原环境/资产。

## 当前在途（必须先检查）

- simple-door-09-0916 / artifacts/R019/door-campaign/episode-0009：已真实执行，路由核实。首次采用 --door-frame-override，另有 --continuous-chunks。已产生真实活动门接触，最大开角约7.49度（检查点时第24动作），尚无成功。完整等待。它在新增完整手部geometry provider之前启动，仍只有末节bounds和公开本体trace。
- simple-apple-05-0916 / apple-campaign/episode-0005：路由/真实动作核实，仍运行；也尚无新的完整手部sidecar。
- simple-bendpick-05-0916 / bendpick-campaign/episode-0005：路由/真实动作和16链接几何sidecar均核实，仍运行。
- 水龙头仍等用户活动件语义回答，human_observation_request.json已存清晰图/问题；不阻塞主线。

完整已审查失败：door8、apple4、bendpick4、faucet3条物理记录；faucet episode2另为零动作基础设施错误。各任务已审计成功均0；抓方块10次门槛已完成，不重做。所有91入口仍保留，19native Sonic兼容；其余桥/资产限制记录未删。

## 本管理回合实质进展

1. 推门8完整：17动作/66.08模拟秒/wall1711.98秒，full turn+skill_update。Astra从自己的公开反馈产生交替步进，双踝累计前移584.6/547.0mm。全3305帧host重建足部接触：左右最长整脚无地面接触各0.26s，最低骨盆.72615m、最大倾斜14.840度，全程站立。不计新尝试或任务成功，不向actor输入重建真值。
2. 推门8操作失败有明确工程原因：双手只碰到固定link_0，活动link_1不动。单块矩形门框mesh被MuJoCo凸包填住洞；记录接触点距原三角面148.15mm，距凸包0.123mm；射线穿过原mesh洞却撞到凸包。证据door-collision-audit-01。
3. RSI新增rsi/simple_door_collision.py：固定frame原始16顶点矩形环精确分四box，仅禁用旧实心凸包碰撞，保留原视觉/惯量；叶片、把手、铰链、摩擦/接触系数不变。原文件不改。源mesh SHA硬校验bd01dac54cb36a782dcb5d589cc7b8e4faaaffff6ecd4ade70358ee8a50679a1。只有显式flag启用，不改变全局默认。
4. 首个同进程双reset对照第二次干扰物身份不同，正确拒绝state恢复；invalid结果保留door-frame-validation-01。改为独立Python进程同seed：door-frame-validation-02-original/fixed，7秒351x80 qpos逐值差0，虚假frame接触消失、同一几何反事实仍碰活动叶片。0模型/0任务信用。9项相关测试通过。door-frame-override-review.json有完整结论。
5. 原始asset003 native close-door与本push-open variant始终区分；新碰撞表示也必须明确标注，不能称未修改native benchmark。台账新增frame_collision_revision和reset_id。
6. 完整机器人手部碰撞几何：rsi/simple_hand_geometry.HandGeometryProvider把16链接/18几何的实际凸碰撞表面写到rollout/episode/hand_collision_model.json（约1.85MB），每帧只给路径/hash与当前链接世界位姿。仅自身机器人；掌部/近端/末端均有，不含物体/接触/奖励。按Python选择body读取，不把整文件倾倒模型上下文。实测闭合1秒后局部顶点差2.78e-16m，位姿更新，hand-geometry-detail-01保留视频/结果。12项geometry/host/recording测试通过。
7. 新door/native runner均已接入新provider并在task spec说明；不热改旧进程。主skill不增加长文，未全局晋升任何locomotion。

## 最近skill/失败审查

- door8 v8 SHA6141ceddca0914094aa84083ee3c56131f55fa0bdec7e5c88116b721ed588cae，713words/6075chars/5346非空白。自主approach候选真实，有支撑滑移/偏航；旧contact barrier假设受碰撞修复影响。9轮task spec只给环境版本说明，未给隐藏几何坐标/诊断动作。
- apple4 v4 SHAe928192894891e11ca4ca6386943461bf08581e6e6331f52ca8ab5abe5d407c5，754/6112/5336；63动作/162.92s，4闭合/抬起试验均未离桌。缩短可见入场路线，下一候选实际对向表面+隔离局部偏移。failure_review已保存。
- bendpick3 v3 SHA05018077b7f1e550f5944d598b3f134794d6e66cb80b28939db6f20e666f7499；52动作/200.72s，左手高入场仍倾盒无保持。
- bendpick4 v4 SHA1307440c2b3eec59d58f2cf0b536017126b143a587270bf48a41262db305695c，765/6118/5332；28动作/113.16s，右手低位姿态跟踪/浅对向失败，进入推移盒子后撤退。新5轮检验改变抓取轴，并用完整手部geometry。

## 下一回合命令

保持每个进程只运行一个episode，必须完整turn/skill_update及失败/成功审查后再启动：
`tools/learn_door_skill.py --pd-profile checkpoint --continuous-chunks --door-frame-override --output artifacts/R019/door-campaign`
本地现有Python=/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python；TMPDIR=RSI/artifacts/R018/tmp，PYTHONDONTWRITEBYTECODE=1，PYTHONUNBUFFERED=1，MUJOCO_GL=egl，PYTHONPATH=RSI:/home/galbot/lizekai/Loco_manip/locomanip/src。
所有>60秒tmux+tee。仿真暂停等模型，不称RTC。每次决策三行，每次诊断先假设/区分标准，每次失败保留原因/证据/排除/下一改变。不要无变化重跑全测试。

## 审计/协作/预算

当前门0/10，IKEA门槛0/3。最新HUMAN_FEEDBACK用户更新覆盖旧API事实：已授权立即使用API推进SIMPLE并行；另一API协作分支的唯一校准费用用户确认为3.39RMB（339分已记账），不能再称全任务付费0。用户已明确停止额外额度/余额/费率调查与重复收费问答，复用既有授权/实测估算/共享账本推进，不以计费研究阻塞任务。本主控当前仍只使用第二账号套餐，未新增付费调用。IKEA仍3次门槛，不读凭据、不提前探资产。共享10000CNY硬限额、每1500报告不变。
R020 gate由既有独立维护者所有。新增碰撞表示与其receipt中original_physics=true字面要求有兼容性问题：已保存artifacts/R019/coordination-request-door-frame-override.json。不得谎称未修改碰撞或静默登记；在实际成功登记前需将override ID、源hash和验证证据纳入gate明确检查。此仅阻塞IKEA登记，不能停止SIMPLE继续。请求尚未转达维护者，不假称已交付。
第二账号最后只读限额account-2-limits-04：ordinaryUsageAllowed=true,pro,通用周期35%已用，0新模型turn/0重置券；该读取发生在主控读到最新“停止额外额度调查”要求之前。此后不再查额度，按明确usageLimitExceeded停止新模型重试，不用重置券/主账号回退。
地面红块由独立thread01a0a888-a98e-70d0-bd7a-0e268a6668ed/ground-to-table写域负责；勿修改或复制。shared core仍主控唯一发布者，候选须跨任务验证与抓取回归才晋升。
既有rsi-simple-continuation-0916继续自然边界接续同thread。结束管理turn前更新supervisor-state.json为continue/blocked/complete；当前仍continue。旧详细检查点存artifacts/R019/supervisor-handoffs，ITERATIONS保留完整历史。

## 新发现并已完整读取的人类反馈交接

ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md现为必须读取的最新要求。已读H001-user-feedback-001/002/003原文；003以抓法条件化包夹判据纠正统一掌心等高归纳。侧抓检查对向指腹与苹果侧面高度/深度重叠；上抓检查包夹开口与能到达两侧的指面，不能要求掌心与果心等高。所有仍human_proposed，不是已验证真相。

视频反馈可持续提供且不要求用户回答；人工求助只针对至少3次可比较自主物理尝试的代表性未解决失败簇，先给连续视频、已试变化、事实/假说和一个问题。不能把基线重执行/回放算3次，不混淆控制器/机制不同的失败；旧水龙头问题不再重复催问。

H001独立复现已冻结完成：65旧动作、10739样本，记录物理/控制精确、RGB在预定阈值内（123/132精确，闭合抬起59-64精确）；不声称全隐藏状态等价，不计新成功。human-feedback/reproductions/H001/status.json里“等待高度参照澄清”字段已过时，被003取代。

H001纠正由现有rsi-h001-correct-0916 / human-feedback/experiments/H001负责，最新status处于rebuilding_fixed_prefix（trial1，旧动作50，新动作0），已明确使用003；不要复制其campaign或改其写域。formal_campaign_success_credit=false；消费结果后再决定新reset迁移。当前door9/apple5/bendpick5仍自主Direct，未热注入人工反馈；未来真正使用反馈须human_feedback_used=true并和Direct分层，human_demonstration_used=false不能改成示教。
