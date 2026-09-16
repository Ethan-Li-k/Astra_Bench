# SIMPLE主控自然接续检查点（2026-09-16）

这是未完成任务的继续检查点，先接管现有tmux/result，不重复开环境。保持第二账号run.sh、Astra/xhigh、workspace-write/自动审批；所有长命令tmux+tee，不按延迟截断推理，usageLimitExceeded停止重试。

## 当前成绩与在途回合

- 抓方块R018已10独立成功，不重做。
- 推门2/10：episode0010和0011完整turn/skill及host独立审计通过；都明确使用asset003-exact-frame-four-boxes-v1。不是原样CloseDoor benchmark。第0012轮进行中。
- 原生BendPick抓盒1次成功已审计：episode0006。无需为最低门槛再开第7轮；经验仅任务候选，未晋升core。
- 苹果0、水龙头0、抓盒放置0。原91任务清单和兼容性工作完整保留，未尝试任务不能当完成。原生CloseDoor也不能因推门变体成功而静默算完成。

在途列表以continuation/supervisor-state.json为准：
- `simple-apple-07-0916`：`artifacts/R019/apple-campaign/episode-0007`，检查时25动作，第二账号实际路由已核实；等完整回合和修订。
- `simple-boxplace-01-0916`：`artifacts/R019/boxplace-campaign/episode-0001`，检查时14动作，第二账号实际路由已核实；等完整回合和修订。
- `simple-door-12-0916`：`artifacts/R019/door-campaign/episode-0012`，检查时10动作，第二账号实际路由已核实；等完整回合和修订。
- `simple-faucet-06-0916`：`artifacts/R019/faucet-campaign/episode-0006`，检查时43动作，第二账号实际路由已核实；等完整回合和修订。

## 本轮关键证据

推门0011：28动作/105.02sim秒，5252完整ticks；终态47.812861度，达标2.70秒，764接触样本，最低base.711942m/最大倾斜15.13996度。2626帧/105.04秒录像。v11 SHA634952e48aba3402b3da04b5cb69a6c15306e1d86cc7fe46d55d02c2d5ca1769，695words6065chars5353非空白。当前自身经验会按新初态选择推手，低臂接近；遇到高位推动停滞，记录stall继续，本轮自主卸载/退手/降手/补步后成功。不是单参数因果隔离，也不是稳健通用行走。`tools/review_completed_door_episode.py --episode ...`复用既有R020 audit_trace保存host审计，不做门槛登记，拒绝覆盖已审计文件。

抓盒0006：63动作/205.28sim秒；原点升86.639mm、末盒底离初始支撑76.393mm。906抬升样本持续对向承载接触，末17.3秒只受手部支持，原生阈值末段2.54秒，但没有单独全高度hold动作。全程站立，5133帧视频。`bendpick-0006-audit`只是已有状态重建，无新尝试。v6 SHAa6d9fd159062efacacc598a09e438a1151669691cadd4bef95381fecdff64152，740/6115/5352。

苹果0006：93动作/223.54sim秒，四个闭合/抬升候选未保持，完整修订后旧合同提前停止，原生in_progress。首次selection/lesson已披露H001语义反馈暴露。`human_feedback_review.json`标明反馈暴露，但未冻结具体版本，不能声称已采用004；原始result不回写。ledger读取该sidecar。v6 SHA963e38139e6e4ff7e1c5705c4df0cfb05954bec10007c221bb98923f95903abe。新apple7冻结004（07:30:26UTC，hash2aa49674accf01bb4229aa4215b8b178b9261d99d1c1d40b758368e6f46ef696）；未来正式苹果也继续显式参数。

抓盒放置新入口`simple/G1WholebodyBendPickAndPlaceTeleop-v0`，spec `ref/tasks/simple-bend-pick-and-place.json`，campaign `artifacts/R019/boxplace-campaign`。已复用原生预检和准则源码；奖励只看盒-篮接触且无手接触，不能当正确入篮或1秒保持。`reviewed-task-sources.json`只列原抓盒v6及其公开rollout，含负迁移边界；actor首次选择确实用了两来源。`rsi/skill_transfer.py`可加载该manifest，限制公开版本/rollout、验证版本hash和作用域，3针对性测试通过（首次测试module调用路径错，改discover后通过，非物理失败）。共享core未改。

## 已修基础设施/过程合同（勿重做诊断）

`rsi/live.py`/`reference_sequence.py`使用相对段时长fsum，合法3秒不会因绝对时刻相减产生3.0000000000000018。LearningHost区分预检ValueError与登记后执行错误；后者取消active，结束物理，仍等完整skill_update，不能重复空turn。水龙头5原27完整turn只有1物理动作/4.4秒；安全自然边界结束后，同episode终止复盘新增1turn/0动作，v4已保存。原result另存。`continuous-duration-fix-review.json`与真实回归02是0任务信用；回归01初始化错已保留。

finish_attempt如今只写policy_stall.jsonl并返回当前观测和下一动作，不结束任务；旧skill被运行时合同覆盖。真正native、安全/系统、物理预算停止保留。20相关测试通过；旧无效mock测试保留且明确不是旧bug复现。原door8历史回执证实提前停。door11在实际任务调用stall后继续并成功，新增真实合同验证。

所有新native回合已有全手部机器人几何侧文件，严禁把host物体/接触真值给actor。单点/连续模式均仍四点ScaleBFM；其他模式/直接关节PD只诊断。旧同IK直驱PD对照已完成，别因旧交接重做。

## 人工反馈与视频

最新HUMAN_FEEDBACK文件已完整读/ACK。只对>=3可比较自主真实失败且仍未解的代表簇求助，视频优先。不要把提前结束、固定前缀回放或不同反馈版本混成3同因失败。H001既有分支3诊断已完成，55新动作，0成功；只有trial1按001-003闭合，trial2/3按004全程张手至预算。固定前缀剩34.36秒，不能证明004无效。`h001-bounded-transfer-review.json`决定继续当前全预算正式apple7，无第4个H001诊断/新人工问答/core晋升，H001写域不改。

apple7启动时视频默认旧Direct页眉未改，`video_label_note.json`纠正为human_feedback_used=true、no motion demonstration；不热改在途录像。已修未来runner按反馈标签显示并在scene_setup保存来源。已有视频和原结果不删除/覆盖。结果按自主/人类语义辅助分层。

## IKEA登记与协作

现在真实推门2/3，IKEA未启动，原资产只读且尚未探索。R020旧schema要求original_physics=true，不能对修复frame撒谎。原名称queue失败，现已从只读线程标题metadata定位既有维护者`01a0a87f-f806-7883-9648-190e49447d86`，精确ID入队成功，message01a0a927-e682-7f41-9d49-5ea32bfcd853。请求`coordination-request-door-frame-override.json`、回执`frame-override-coordination-queue-exact-id.txt`。只入队，尚未见ACK/修订；维护者独占tools/coordination，不另写重复gate、不建新通用代理。不修改内部会话数据。检查其现有交付再登记；SIMPLE不因此停。

地面红块独立主管thread01a0a888-a98e-70d0-bd7a-0e268a6668ed及其写域保持独立；先前durationfix已正规入队转交。唯一共享core发布者仍本主控，跨任务/回归前不晋升。

预算10000元全任务共享，每1500元报告，最新用户要求停止额外额度/余额/费率调查。其他API分支校准3.39元已确认，本主控0付费调用，不能写全任务0。不要读api.json/auth.json、不消费券、不回退账号/模型/API。付费并发预留由已有组件负责，真实约束未满足只阻塞付费分支。

## 下一管理回合执行

1. 读AGENTS、PARALLEL/HUMAN_FEEDBACK最新、api-budget、R020 inbox、ITERATIONS；先检查tmux/result，接管四个现有回合。
2. door12完整后先审查失败/成功和skill；成功可复用现有host审核脚本，失败保存原因/证据/排除/下一改变。推进后续独立重置直到10，不以启动算完成。
3. faucet6、apple7、boxplace1各等完整turn+skill，保存审查再下一回合。原生容器接触需另审视觉/几何是否正确放置。
4. 下一正式苹果命令必须保留`--human-feedback human-feedback/H001-user-feedback-004.json`。不要把未成功H001候选当验证规则。
5. 成功达到3时推进IKEA门槛登记及既定分支，不篡改碰撞provenance；同时继续SIMPLE。
6. 更新ITERATIONS、campaign_audit和continuation/supervisor-state.json。仍可推进写continue，只有全范围完成才complete。推理慢不是blocked，不中止在途。

命令使用既有Python `/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python`。env沿用TMPDIR=RSI/artifacts/R018/tmp、PYTHONDONTWRITEBYTECODE=1、PYTHONUNBUFFERED=1、MUJOCO_GL=egl、PYTHONPATH=RSI:/home/galbot/lizekai/Loco_manip/locomanip/src。
推门：`tools/learn_door_skill.py --pd-profile checkpoint --continuous-chunks --door-frame-override --output artifacts/R019/door-campaign`。
水龙头：`tools/learn_simple_task.py --env-id simple/G1WholebodyOpenFaucetTeleop-v0 --task-spec ref/tasks/simple-open-faucet.json --continuous-chunks --output artifacts/R019/faucet-campaign`。
苹果：`tools/learn_simple_task.py --env-id simple/G1WholebodyPickAndPlaceAppleTeleop-v0 --task-spec ref/tasks/simple-pick-place-apple.json --human-feedback human-feedback/H001-user-feedback-004.json --output artifacts/R019/apple-campaign`。
抓盒放置：`tools/learn_simple_task.py --env-id simple/G1WholebodyBendPickAndPlaceTeleop-v0 --task-spec ref/tasks/simple-bend-pick-and-place.json --continuous-chunks --output artifacts/R019/boxplace-campaign`。
