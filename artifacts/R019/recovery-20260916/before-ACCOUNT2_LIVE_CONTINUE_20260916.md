# SIMPLE 主控自然接续检查点（2026-09-16，5/10）

先读最新HUMAN_FEEDBACK到末尾；再读AGENTS、PARALLEL_SKILLS、api-budget、R020 inbox与ITERATIONS最新。旧文案不能覆盖最新“不查额度/余额/费率”、非终止finish_attempt及H001004。保持第二账号run.sh、gpt-6-astra/xhigh、workspace-write/自动审批。所有长命令tmux+tee；完整等待模型turn与skill_update，usageLimitExceeded立即停重试。此为未完成任务接续，禁止另建campaign或watcher。

## 已审计进度

抓方块R018的10独立成功已完成，不重做。SIMPLE推门现5/10：episode0010—0014均完整turn/skill及独立host审计通过，使用明确的asset003-exact-frame-four-boxes-v1，不称原样CloseDoor benchmark。BendPick抓盒episode0006已有1次审计成功，不需要为最低门槛重复。苹果/水龙头/抓盒放置均0审计成功，其余91入口范围保留，未做的不能删掉或当完成。

最新door14：23动作92.62模拟秒，开36.115905度、保持2.88秒、879手门接触样本；最低base.714352m/最大倾斜14.995232度，全程站立。2316帧92.64秒录像，v14 SHA5c1ca23b1be27271a1409942fef57e5a70d0664c21f63125bb80db2779d7ee36（667words6022chars5336非空白）。完整手部净空与腕高度不等价；本轮重新调整腕姿/手部净空后成功，未晋升公共core。

最新door13：34动作130.86秒，开32.028048度、保持1.64秒，3272帧；v13 SHAac59414834a055a8848422f04a2d2f50aa4323f99892de9674244f43b0f2daa6。两次finish_attempt均继续本回合，卸载/重定位/再推成功。12也已完整成功并审计，证据各在success_review.json。踝上升和被动脚移动不等于整脚离地或可靠步行。

## 在途回合：必须接管而非重开

最新精确快照以codex-account-2/continuation/supervisor-state.json为准，保存时：

- simple-door-15-0916：door-campaign/episode-0015，13动作，真实第二账号路由已验证。
- simple-apple-07-0916：apple-campaign/episode-0007，120动作，显式冻结H001004，真实路由已验证。
- simple-faucet-07-0916：faucet-campaign/episode-0007，51动作，真实路由已验证。
- simple-boxplace-03-0916：boxplace-campaign/episode-0003，33动作，显式--verified-placement，真实路由已验证。

四者均尚无result；不要因为慢推理、旧tmux名或动作数多而中止/重置。等完整turn/completed、skill_update、result和录像，然后审查再运行下一独立回合。所有actor仍四点ScaleBFM；host审计真值不得提供给actor。每项决定前写当前问题/总目标/不可重犯的错误。

## 水龙头6审查与7轮方向

6完整64动作241.10模拟秒，预算截断in_progress，0成功；25到位39超时，wall2468.08秒，6028帧241.12秒录像完整。v5 SHAb2ff63d0f262acc3f74be62f4c29e34b795b9750e9ba79d2e94db85dd6e6c929（698/6036/5320）。finish_attempt在3/27动作只记stall，继续到64。自身56/59动作有部分踝移动，但未审计全脚离地，不称可用步态。7轮提前利用自身换位观察候选，先建立活动特征可见关系，再试接触；不提供host杆/轴位置。failure_review与faucet-0007-plan保留。

## 抓盒放置假阳性与显式新完成合同

boxplace1原生success在22动作94.94秒触发，尚无抬升/搬运/释放。boxplace2仅3个全张手动作15.02秒也原生success；4个native真样本，末native=false，盒最大升高仅19.1mm。两轮完整推理/修订，但success_review均audited_task_success=false，原始result不改。最终RGB盒在篮边/外侧，不能算放置成功。v2 SHA0b0721f13558c7ff67716aa167bd993299be843e74e1f0fb09ef983c1a19f090。

新rsi/simple_placement.py只经--verified-placement启用，限BendPickAndPlaceTeleop：先同手拇指+对向指承载、无外部支撑的5cm抬升保持.5s，再无机器人/其他支撑的native-qualified容器支持保持1s。掉落/桌面支撑断开阶段连续性；无支撑释放过渡最多.3s。最终几何仍须独立审计，不能把门槛通过当自动正确入篮。原生奖励调用、每帧原始flags、布局和物理不改，不是原样benchmark。

验证：5时序/接触/安全测试+2录像回归通过；两旧假阳性原记录的高度/时间/native flags在有利接触假设下仍不满足门槛（不是完整动态回放）；真实seed3初始化+25tick/.5s无模型集成通过、录像保留、0任务信用。review在artifacts/R019/placement-gate-review。boxplace3是首个正式启用回合，scene_setup/workspace已冻结合同，日志仍可继续。视频旧默认页眉由video_label_note.json说明，新加载runner会显示verified placement variant。

计数已修：audit_simple_campaigns以host_success_complete、complete_host_successes及completion_contract分层，原生SimpleNativeEvaluator单列complete_native_evaluator_successes。audited_task_success仍要求完整turn/skill且独立review=true。学习runner的successes也只用审计成绩，不能把两旧假阳性当成功经验。用真实door14/boxplace1,2,3/bendpick6做了5项分层核验。未来结果增加configured-host语义字段；旧raw结果不回写。

## 既有控制/结束规则：不要重做

finish_attempt只记录policy_stall并返回继续动作，不设置finished。保留native、安全/系统、物理预算终止。原始有效旧实现失败复现在artifacts/R022/finish-gate-candidate/logs/02-baseline-red.log；01导入错误无效。独立工程交付R022/finish-gate-applied已复核，23测试通过；主控早先无效mock不冒称复现。door11—14实际stall后继续成功验证已生效。不再重复写同一修复。

3秒浮点边界已用相对时长fsum修复，post-admission执行错误不能被no_execution掩盖。水龙头5是1真实动作4.4秒、27原完整turn，另加1个同episode终止复盘turn/0动作；不是28尝试。duration真实回归02已通过，不重做。旧同IK直驱PD、碰撞诊断已完成，不因旧交接再跑。

## 苹果/H001与其他协作边界

苹果7明确--human-feedback human-feedback/H001-user-feedback-004.json，来源hash2aa49674accf01bb4229aa4215b8b178b9261d99d1c1d40b758368e6f46ef696，采用时刻07:30:26UTC。侧抓先同平面/包络可见再闭合，不以小闭合绕过。没有动作示教；与自主Direct分层。视频旧Direct标题有既存说明sidecar，勿热改。在途不注入新规则。

H001独立3个诊断已完：固定前缀只剩34.36秒；trial2/3采用004但未到合规闭合，不能宣称004已被三次抓持失败否定。没有新人工问题；苹果7完成后审查实际可比较探索与失败机制，至少3可比自主物理尝试仍不解才请求代表视频分析。不要重复问已答高度语义，不复制H001环境。

地面红块独立主管与reviewer写域ground-to-table保持独立，用户发来的移桌.55m轮仅diagnostic，恢复原桌位由对方负责。PEER_OUTBOX提交后再按适用性/负迁移/回归审查，不复制其campaign。公共core本主管唯一发布，当前未改。用户其他API/architecture会话正在运行，不干扰、不重复角色研究。

## R020门槛与IKEA进展

既有R020维护者完整交付，schema2支持准确绑定frame override，41离线测试不算物理。主控签发10/11/12收据并登记成功，physical-gate-state=3通过；额外13/14已有审计，不必为既已满足门槛重复登记。original_physics=false不能改true。tools/coordination归原维护者，不复制组件、不建立新watcher。

IKEA在第三次独立审计之后实际开始只读资产分支，artifacts/R023/ikea-door/entry.json记录时刻与hash。原资产/home/galbot/Downloads/APA/IKEA_LivingRoom_Mesh_0915未改。用户参考ref/tasks/20260915-210156.jpg。

现有ds4090 SIMPLE .venv的USD22.11可独立加载pxr，但原主/Flatten USD因RÅDMANSÖ家具Unicode prim路径被解析器拒绝。两错误日志保留，不称源文件损坏。无安装/下载/环境修改。远端新staging为/home/lidanshi/lizekai/RSI/ikea-r023，旧门Isaac重渲染不重做。

已复用本地SIMPLE .venv/lib/python3.10/site-packages/cmeel.prefix/bin/assimp，并只为该命令设置同prefix/lib，解决错误库解析；FBX info成功，未后处理XML为469节点/141mesh，保存fbx-scene.assxml/fbx-structure.json。FBX GlobalSettings UpAxis=1/UnitScaleFactor=1；预览采用(x,y,z)->(x,-z,y)*.01。

preview05静态图确认电视/柜体/右侧棕门对应Door_West。门与把手分离；原艺术家门旋转pivot=(.000038,1,13.499997)，把手pivot=(2.500038,88.699989,109.099998)，均FBX原单位。不是验证好的物理轴/锁舌。原FBX门闭合，参考图半开。原USD的物理仍未读出，不能声称等价。派生PNG纹理逐像素相同，UV原点已修；光照/粗糙度/地面尚非完整原RGB。

工具tools/inspect_ikea_usd.py、tools/preview_ikea_fbx.py。preview01平面惯量、02JPEG格式、03相机朝外问题及04/05修正全部保留，无physics/actor/任务信用。asset-feasibility-after-preview.json给出证据与下一步：RSI-only明确变体的铰接物理适配，验证frame/leaf碰撞、轴向、重力与闭门reset，之后才能模型尝试；不得把静态图/mesh分离当成功。

IKEA/main本轮0付费调用；API-ground其他分支已有3.39元校准和未结算后续调用，最新tmux rsi-api-ground-002-0916存在，不冒称全局0或只有3.39。最新用户允许现有实测估算推进，禁止额外额度/费率研究；复用既有共享账本、并发预留与运输接口，不读凭据内容、不另写计费框架。不以该问题暂停SIMPLE。

## 下一管理回合执行

1. 接管四个在途回合，完成turn/skill/result后分别审查，更新ITERATIONS与ledger；door优先推进到10独立成功。
2. door下一轮同控制/场景，按当前自身skill与公开经验选择，不用host隐藏状态。已存在success_review就读取，review脚本拒绝覆盖。
3. 苹果后续继续显式004，水龙头后续在完整失败复盘后改变可区分的假设。boxplace后续必须保留--verified-placement，审查最终几何和阶段连续性。
4. IKEA推进新文件物理适配，来源/变体/初态明确；不重做静态预览或无限寻找解析器，不动原资产。
5. 使用既有rsi-simple-continuation-0916唯一零模型接续器。自然结束前supervisor-state写continue并清楚交接；真正额度/必要外部阻塞才blocked，全范围完成才complete。

命令用既有Python /home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python，env TMPDIR=RSI/artifacts/R018/tmp、PYTHONDONTWRITEBYTECODE=1、PYTHONUNBUFFERED=1、MUJOCO_GL=egl、PYTHONPATH=RSI:/home/galbot/lizekai/Loco_manip/locomanip/src。

推门：tools/learn_door_skill.py --pd-profile checkpoint --continuous-chunks --door-frame-override --output artifacts/R019/door-campaign
水龙头：tools/learn_simple_task.py --env-id simple/G1WholebodyOpenFaucetTeleop-v0 --task-spec ref/tasks/simple-open-faucet.json --continuous-chunks --output artifacts/R019/faucet-campaign
苹果：tools/learn_simple_task.py --env-id simple/G1WholebodyPickAndPlaceAppleTeleop-v0 --task-spec ref/tasks/simple-pick-place-apple.json --human-feedback human-feedback/H001-user-feedback-004.json --output artifacts/R019/apple-campaign
放置：tools/learn_simple_task.py --env-id simple/G1WholebodyBendPickAndPlaceTeleop-v0 --task-spec ref/tasks/simple-bend-pick-and-place.json --continuous-chunks --verified-placement --output artifacts/R019/boxplace-campaign
