# SIMPLE恢复后的管理接续点 — 2026-09-16 10:40 UTC

这是同一主管thread 01a0a867-d7aa-71f2-8547-e264d6d09ede的接续；先核对现有tmux、result、完整turn与skill_update，不重复启动。最新精确计数/活动回合以 supervisor-state.json、campaign_audit.json、PROGRESS.md 为准。

## 最新指令与所有权

完整读AGENTS.md、SIMPLE_EVAL、HUMAN_FEEDBACK到末尾、NO_TRUNCATION_SHARED_SKILLS、PARALLEL_SKILLS、api-budget、R020 inbox和ITERATIONS最新段落。旧API查询/旧IKEA执行归属已过期。本主管只做SIMPLE；IKEA和API搬运各自owner，不接管或启动其任务，不查额度/余额/费率，不读凭据。第二账号run.sh、Astra/xhigh不变；长任务tmux+tee；无新通用子代理，无真机。

公共core仍本主管唯一发布者，本轮未晋升。框架正式辅助queue 01a0a94d-6143-74c0-80cd-03d0b61acaf0；搬运恢复owner 01a0a982-cec5-71c0-b771-091c31df61f2。公共原子经验统一artifacts/R019/public-atomic-experience-20260916.json，有hash/条件/反例。只给公共轨迹，不给host真值、实时tracker或世界目标。

## 重启已处理，绝不可回等door15

现boot102fa58c-22af-4d56-bc78-f297d64f2a51；旧door15 boot3d81b4d6-590c-44a9-9ae2-6735f2f9480d。旧15保留61动作；最后物理回执已episode_step_budget，但之后无完整turn/result/skill_update，归基础设施中断。MP4缺moov不可解码，原文件未删。没有完整physics/tracker checkpoint，因此16起为新reset，不是旧回合续接。证据recovery-20260916/door15-interruption.json、原episode/infrastructure_review.json。

恢复主管锁定rsi-simple-recovery-0916/PID292946/startticks255172及recovery-20260916T095038Z.jsonl。唯一SIMPLE watcher rsi-simple-continuation-0916已绑定active-supervisor.json，等待此主管完整结束与退出；不能并发resume。修复含boot/PID起始tick/新状态校验，11针对测试通过。工具自己的/proc并非宿主视图；需要真实存活核验用tmux宿主readonly脚本，不能据此误杀/重复启动。最新证据recovery-20260916/live-handoff-liveness.json；精确SIMPLE watcher计数1。其它owner的watcher独立，不混数。

## 审计成绩及完整回合

R018桌面抓块10次已完成，不重做。SIMPLE门7/10：10—14、16、17审计成功，15中断不计；门是明确asset003-exact-frame-four-boxes-v1推开变体，不抵扣原生CloseDoor。最新17：34动作119.24s，39.802度/4.74s，v16；16：25动作96.36s，32.681度/1.64s，v15。各success_review.json绑定视频/重置/完整turn/修订；review_completed_door_episode.py拒绝覆盖既有审计。

BendPick6：1审计成功。水龙头8：11动作31.38s，原生角度-0.799896rad，v7，1审计成功；原生双reward调用逐帧复算，无1秒/撤手保持附加要求。放盒4：51动作230.28s，强化acquired-lift-then-released-container-support-v1，最终释放后篮支撑2.8s，独立几何仅篮接触，v4，1审计成功；盒高于篮沿，不宣称全容积装入，无独立退手/持物行走。旧boxplace1/2假阳性仍被否决。

烤箱1：14动作53.44s，最终joint2=1.57196rad，双目露出炉腔，终态无手接触，v1，1审计成功。垃圾桶1：5动作16.62s，盖0.533603rad，原生reward复算一致，v1，1审计成功；手仍接触，没有撤手保持验证。以上审计脚本/几何证据都在recovery-20260916，诊断本身不计新尝试。

91注册入口保留，task-evaluation-status由audit_simple_campaigns.py从真实campaign同步；19native接口已预检可用，另66兼容性未决、6现接口不适用，不能把预检当成绩或静默删除。其余可用任务继续逐项详细spec、独立reset与审计。

## 当前实际在途（保存时，必须再次核对）

- simple-door-18-0916：door episode0018，加载v16，至少11动作，仍in_progress；新权限合同已实际验证。
- simple-apple-08-0916：apple episode0008，显式H001004，约96动作，物理预算未结束；不可热注入或重开。仍0成功。
- simple-chair-01-0916：chair episode0001，已有实际动作，新权限合同已验证；向桌推椅，不得只以原生绝对X位移0.8m当正确方向完成。
- trashcan1已完整审计，无需重复开。烤箱/水龙头/放盒已达到最低1次，释放并行位给未尝试任务。当前可再准备一个独立新任务，但先读其原生语义与已有预检，避免重复诊断。

## 已发布框架/相机/权限修复

ARCH-REVIEW与MEMORY-PRIORITY已完整ACK并以combined-compatible.patch逐hunk集成。原入口已归档压缩，原memory版本完整保留；实际skill+runtime<=831words/6250chars/5357非空白，在发送前、skill_update写入前检查并记录SHA。审计否决/未知/合同不匹配success不置顶。真实door16/17、faucet8、boxplace4、oven1已完整调用链验证；input与revision总长见各policy_instruction_budget和memory日志。共享核心未变。不能把并变入口/标定/检索和不同reset作单因收益结论。

相机mujoco-render-frustum-v1已修实际MuJoCo显式intrinsics渲染与旧fovy估计不符；新观测提供fx/fy/cx/cy及像素中心合同，机器人几何可用于核对。原物理/图像未改，旧经验中的fovy坐标或经验拟合必须复核。测试/本机场景证据camera-calibration-review。

真实旧app-server返回readOnly/never，已按用户要求修为明确workspace-write/on-request+auto_review，connect校验权限再发turn。9针对测试及第二账号零模型握手通过；首次正式生效门18、trashcan1、chair1，旧在途保护。rsi/codex_app_server.py新的基线已发框架queue，NT候选不可覆盖。证据permission-contract-fix.json与permission-physical-route-verification.json。

NT仅先采用turn/start无限等待和未知ACK锁；完整closed-network自动续接仍待中间failed-turn落盘与审计接合，框架在rsi-continuity-audit-0916跟进。未闭合错误通知、重启丢状态和未知物理请求绝不自动重发。当前run_turn无推理deadline；finish_attempt只记非终止stall，已真实继续并成功，不重做修复。物理预算、安全、模型自然完成、断线、重启各自分类。

## 用户反馈/UI与下一步

苹果继续H001004侧抓：先张手同平面/包络可见，不能试闭合绕过；高度语义已答，不再重复问。旧H001复现分支已完，诊断不凑3次真实失败。人工求助需至少3个可比较自主真实终态失败；预算、提前终止、系统中断不混算。

DASHBOARD-20260916已ACK，现有http://127.0.0.1:8765由01a0a980-7943-7963-9f36-b9c43c90c2da唯一UI owner维护。本主管只写原progress/PROGRESS/ledger和episode/public-progress快照；UI原有固定子任务列表可能滞后新oven/trashcan/chair，已queue且未当完成。各campaign progress成功计数需在独立review后刷新，runner写result时审计可能尚pending；不改原result。用户回答接口OWNER_INTERFACE已读，可自然边界消费新不可变回答/ACK，不把工程交接当人工任务反馈。

下一管理回合先接管现有三轮，完整等turn、skill_update、result及录像，逐轮审查，再运行一个独立下一回合。门优先到10；已最低完成操作任务不重做。继续更新ITERATIONS/PROGRESS/视频入口和公共经验；发布共享core前仍需跨任务适用性、负迁移和回归。只有全SIMPLE范围完成才complete；还能推进写continue，真实额度/必需外部阻塞才blocked。不得因回复用户结束就终止后台推理。

运行脚本均在artifacts/R019/recovery-20260916/run-*.sh，现有SIMPLE解释器/离线资产复用，无安装下载。正式actor只有四点ScaleBFM，所有模型经第二账号run.sh，Astra/xhigh；暂无真机/RTC/Isaac物理声称。
