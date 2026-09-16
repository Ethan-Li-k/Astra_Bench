# 六类聚焦：暂停已核验，技能候选未部署

本轮固定第二账号 openai / gpt-6-astra / xhigh。没有新模型实验、付费调用、物理回合、环境或监督器。唯一 SIMPLE publisher 继续持有现场调度；本轮不发布 shared core。

## 已完成的暂停

[暂停回执](pause-status.json)与[前后进程证据](pause-evidence/process-after.json)显示：

- **IKEA apple-0002 已停**。先归档 state/actor-progress、公开动作历史及 PID/start ticks/父子关系/tmux 绑定。runner 没有 PAUSE 消费入口；PAUSE 只阻止下一次 owner 接续。最后完成工具边界为43动作、152.72仿真秒。对其独占 app-server 两进程发送定向 SIGTERM，使现有 caller 经 EOF 的 except/finally 封口录像；对正在继续的 IKEA manager 发送定向 SIGINT。actor、app-server、编码器、owner 及 continuation watcher 全退出；保留无模型 heartbeat。没有 SIGKILL、进程名通杀、代码热改或共享服务操作。
- 原 result 原样为 `terminal_kind=system / EOFError`，没有伪改成完整物理失败；此次**行政原因明确是 user_requested_pause**。协议有15次 turn/start、14次 completed，第15次无终态；不能冒称完整 turn，远端结果未知且不重发。原 skill 未更新。录像 ffprobe 可读，3819帧/152.76秒；“录像封口”不等于“推理完成”。[信号回执](pause-evidence/cancellation.json)、[协议元数据](pause-evidence/ikea-protocol-lifecycle.json)、[录像](pause-evidence/ikea-video-ffprobe.json)。
- **地面 episode-0005 已停**。原 actor 和 owner 绑定 PID 均不存在；watcher456959 的启动 ticks397394、cwd/父关系一致，无子进程，处于阻塞休眠。源码 `blocked()` 不再启动模型。保留 PAUSE、HTTP429 原回执、005封口视频，以及002-call55 /004-call43 /005-call10未知请求。没有重新唤醒 owner 或发送任何新 API。[录像](pause-evidence/ground-video-ffprobe.json)。

IKEA state/actor-progress/web-progress 仅追加 `user_pause`；原字段、result、轨迹未覆盖，修改前副本在 pause-evidence。旧 state 的 `continue` 是保留的历史字段；实际暂停以新 overlay 与进程回执为准。原先 IKEA 接管/ACK 请求已被本次明确暂停指令覆盖，不按旧请求恢复探索。启动取消脚本的首次调用因 Python 无 pidfd 支持在发信号前退出；改用已有系统 Python 的 pidfd，未创建环境或绕过审批。

## 值得改变的是阶段判断，不是再建框架

旧[架构评审](../REVIEW.md)的短 skill、按需公共经验、目标/测量分离继续适用。第一参考 [GPT-as-Policy 控制合同](snapshots/ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md:9)区分测得关节/EEF与夹爪命令、要求 ACK 后检查；这里只复用该思想，不搬用 ARX-X5 数值。RoboRSI 仅沿用此前已审的原子经验/适用前提，不重做平台、MoE或训练研究。

1. **用可观察阶段解释 timeout。** 从原公开 history 重算：XMoveBendPick1=49动作/46 timeout/0含闭合动作；BendPickSim1=65动作/44 timeout/18含闭合动作，见[重算证据](review-evidence/phase-timeouts.json)。两者均物理预算结束且已有完整修订，不是推理截断，也不是同因的49/65次抓持失败。前者优先区分接近、姿态追踪、可见包络；后者还需检查被推移目标的重定位、计算后审阅、抬升/留握检验。单回合多次探测不凑3次独立可比失败。
2. **包络→闭合→小抬升→独立留握再观察，是条件模板。** 木块437/438、BendPick6、XMovePickSim1支持检索后适配和独立 hold；不能拷贝坐标、闭合序列或 mesh/capsule 假设。BendPick6 无另做最终8cm后 dwell；XMovePickSim1 的独立 hold 位于最终原生门槛前，无额外终态 dwell，不抬高旧成绩定义。保持稳定站位、达到的腕姿、全手扫掠净空与新标定图像同看；计算几何拒绝干涉，不证明接触。
3. **Handover 必须按注册变体验收。** 原生 `HandoverTeleop` 与 `BendHandoverTeleop` 累积目标—容器接触奖励；`HandoverSimToRealTeleop` 累积目标—左手接触；PlaceBack 记录曾右接触→左接触，再判桌面支撑且无手接触。它们都不能单凭名字证明交出手卸载后的真实留握。精确源码/行号见[TASK-PLAN](TASK-PLAN.md)和[只供review的准则](review-evidence/handover-mobile-native-criteria.json)。库存 `review_required=false` 不是语义充分证明。现有 auditor 已要求完成turn/修订及独立 success_review；不重做该修复、不把弱触发自动算转手成功。
4. **Mobile 保留现有完整阶段合同。** 当前 mobilecheezit task specification 已写明拾取、真实持物移动、第二桌释放；不重复实现。共享空手接近和原地释放方法，持物步行仍待真实证据。[当前任务](snapshots/ref/tasks/simple-mobile-pick-place-cheezit.json)。
5. **本体可见性已上线路径不再诊断。** XMovePick3已有首动作验证和完整成功审计；H001004、新 reset、skill、观测并变，不能归因新字段。此处只在模板提醒看测量，不改控制器、阈值或要求额外物理等值测试。

## 交付方式与保持项

[candidate/loco-manip-direct/SKILL.md](candidate/loco-manip-direct/SKILL.md)是一份共用短模板；[deltas](candidate/deltas)是六份很短的任务差异，每次只拼入**一个**。不整包替换已学会的任务入口，不热改在途；publisher 可仅摘取当前任务需要的阶段修订，保留原 memory/版本/失败和公开来源。[复用来源](experience-map.json)与[应用顺序](INTEGRATION.md)分开记录。

现有 `SkillMemory.read` 已将成功优先条件限制为原生success、host审计passed、审计成功true且 completion contract 匹配；未知/否决/未完成/不匹配只可作为最近记录或反例。审计在 update 后完成也会由读取时 callback 重新查询，原 outcome不重写。只传既有选择标签，不传 audit payload/路径/隐藏值。保留这一实现，当前无需第二套成功系统。[源码快照](snapshots/rsi/skill_learning.py:35)。

按实际 caller 的 immutable+NETWORK_CONTINUATION 总计1982字符预留，各组合701–716 words /5200–5333 chars /4490–4613非空白，三项上限均通过；无静默截断。Grasp模板通过静态检查不授权启动。没有模型行为或物理收益测试；候选不可冒称已集成或泛化。[长度与拒绝超长检查](checks/length-validation.json)、[skill校验](checks/skill-validation.log)。
