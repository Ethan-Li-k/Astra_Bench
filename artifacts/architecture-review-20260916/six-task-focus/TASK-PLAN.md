# 六类任务合同与下一自然边界安排

证据快照见 [task-status.json](review-evidence/task-status.json)。这是一次有限读取，不是新监督器；在途动作数随原 supervisor 继续更新。历史成功是学习基线，未新增冻结评测成绩。所有所列物理为 SIMPLE/MuJoCo、推理暂停物理，非 Isaac/RTC/真机。

历史来源：桌面10次审计原生成功/15次有物理尝试，10个ID仍用此前完整[状态证据](../status-evidence.json)，其中5次末态保持原成功判据；门10次为明确修复门框 push-open 变体，ID0010–0014及0016–0020，[里程碑](snapshots/artifacts/R019/door-campaign/ten-success-milestone.json)。不重放凑数、不把门方法视为持物行走。

1. **XMovePick**：主入口 `simple/G1WholebodyXMovePickTeleop-v0` / `xmovepick-campaign`，原苹果任务9cm；历史成功 episode0003（31动作，H001004语义反馈辅助，非示教）。`G1WholebodyXMovePickSimToRealTeleop-v0` / `xmovepicksim-campaign` 是另一箱体/3cm变体，episode0001成功（38动作，审计记无人工反馈）；两者各记1，不能相加成同任务2次。原主入口已满足本阶段最低1，下一步以公开经验供迁移，不为配额重开。阶段：有实际身体/足部接近→站位可达且视野稳定→全手包络→闭合→小抬升共动/独立hold→本任务终态。[原任务](snapshots/ref/tasks/simple-xmove-pick.json)、[变体](snapshots/ref/tasks/simple-xmove-pick-sim-to-real.json)。

2. **BendPick**：`simple/G1WholebodyBendPickTeleop-v0` / `bendpick-campaign` 原8cm任务历史 episode0006成功（63动作，审计明确无人工反馈；旧result未写该字段，原件不补造）。`G1WholebodyBendPickSimToRealTeleop-v0` / `bendpicksim-campaign` 为3cm变体，0001预算结束，0002仍在途，快照37个完成动作；不热改，结束后审查。阶段：站稳/可见低位目标→可达腕姿/扫掠净空→包络→闭合→小抬升/独立hold→相应高度。第一轮成功原入口已达最低1，不将SimToReal尝试冲抵或倒扣。[原任务](snapshots/ref/tasks/simple-bend-pick.json)、[变体](snapshots/ref/tasks/simple-bend-pick-sim-to-real.json)。

3. **Handover**：当前R019没有该族campaign/已审成功，本次只交合同候选。为“真实手间转移”优先建议 publisher 审阅 `simple/G1WholebodyHandoverSimToRealTeleop-v0`；启动前明确 giver/receiver、承载和终态口径。其它三个保留注册候选，不全部开测：`G1WholebodyHandoverTeleop-v0`、`G1WholebodyHandoverPlaceBackSimToRealTeleop-v0`、`G1WholebodyBendHandoverTeleop-v0`。沿用G1/Sonic四点caller与原控制，不选MP/新机器人。

   host-only合同审查：原 Handover 用容器接触累计0.1、默认阈值0.9，[源码:354](snapshots/external-task-definitions/g1_wholebody_handover_teleop.py:354)；BendHandover用容器接触累计0.015、metadata阈值0.6，[源码:338](snapshots/external-task-definitions/g1_wholebody_bend_handover_teleop.py:338)。SimToReal的真实执行 reward 调用左手接触判据，[源码:253/275](snapshots/external-task-definitions/g1_wholebody_teleop_efficiency_tasks.py:253)。PlaceBack的曾右接触→左接触状态机不要求交出手释放后 receiver 单独保持，[源码:393](snapshots/external-task-definitions/g1_wholebody_teleop_efficiency_tasks.py:393)。不要因为存在名为handover的未使用 helper 而错判实际奖励路径。

   阶段证据：giver离开外部支撑后的承载→receiver可见包络/共动→giver逐步释放并离开→receiver单独保持→若是PlaceBack，再检查受控落桌/放手。原生信用与真实转手分别保存。若原生提前结束而后段无证据，先停动作并记“未验证”，审计不授予真实转手成功/成功优先经验；需要延后终止时由唯一publisher另行明确带版本的加强合同，保留原生reward，不能在本次静默改标准。每族最低1，不默认四变体都加配额。

4. **Mobile P&P**：继续 `simple/G1WholebodyMobilePickAndPlaceCheezitTeleop-v0` / `mobilecheezit-campaign/episode0001`，无已审成功，快照56个完成动作仍在途。保留当前[已有合同](snapshots/ref/tasks/simple-mobile-pick-place-cheezit.json)。阶段：空手接近→真实拾取/独立留握→带载离开第一桌→载物与机器人同步移动到第二桌→可控下放→手释放/目标稳定支撑。原生仅检查第二桌顶接触且无手接触，[源码:641](snapshots/external-task-definitions/g1_wholebody_teleop_efficiency_tasks.py:641)，不能替代前段carry证据。XMovePickSim1和boxplace4可以供选，均未证明持物步行。保留本回合到自然边界，不另起并发者。

5. **Grasp**：用户入口澄清仍待回复，其余五类不因此等待。最多保留两种映射：A=原R018桌面木块10次历史基线，仅共享抓取模块；B=注册 `simple/G1TabletopGraspMP-v0` 对应用户所指SIMPLE G1桌面语义，**不是本轮默认选项**。B的inventory标记native_sonic=false，现有runner会拒绝，不能通过导入MP示教轨迹/换机器人控制来绕过。用户确认B后还需owner兼容合同；本轮没有新Grasp物理尝试或新配额。只交公共包络/闭合/小抬升/hold模块，不声称A等于新SIMPLE测评。

6. **XMoveBendPick**：`simple/G1WholebodyXMoveBendPickTeleop-v0` / `xmovebendpick-campaign`，8cm低桌箱体。当前无已审成功；0001、0002已有result，0003仍在途，快照23个完成动作。保留 [v1反例](snapshots/artifacts/R019/xmovebendpick-campaign/memory/versions/0001.md)。阶段：实际接近→稳定可达姿态→低位全手净空→包络→闭合→小抬升/独立hold→任务终态。未闭合的reach timeout先处理站位、腕姿与视野；只有实际闭合后的保留探测才能讨论相应抓持阶段，不能直接归因为摩擦。[已有任务](snapshots/ref/tasks/simple-xmove-bend-pick.json)。

## 一次新正式评测如何固定与验收

沿用原 supervisor，先完成在途三回合。已达标作为历史基线，不强行重开；未达标依真实新证据决定下一回合，最低每类1，不擅自升级10或批量铺设任务。每次独立reset前pin注册名/任务变体、completion contract、接口/相机/机器人几何版本、skill+delta+runtime hash、controller/PD、seed、human-feedback来源与层级、既有物理预算。开始写所选原子经验和必须重新确认的条件；无兼容证据明确不迁移。

每阶段记录一个可观察进入/继续门槛及失败分类；一次动作同时写预期变化、实测位姿/姿态变化与追踪残差，失配时修改有依据的假设，不凭目标姿态晋级。安全、预算、系统、用户暂停与物理任务失败分开。至少3个同阶段、同机制、可比独立真实失败才考虑求助；主动人工反馈仍单列。

成功验收沿用完整turn序列、独立reset、skill_update、host-success和任务审计；保存成功/失败原录像与轨迹。原生阈值与独立语义审计并列，旧回放/诊断不加新计数。学习中可版本修订；冻结评测另开记录并固定策略，不能把本轮学习成功宣称留出泛化。只在完整新证据、合同改变或已复现错误时触发局部review；不每动作叫四角色，不增加新平台。
