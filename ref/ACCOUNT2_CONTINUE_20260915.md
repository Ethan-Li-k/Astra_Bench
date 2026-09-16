# 第二账号继续 RSI 自主仿真任务

用户明确要求通过 `/home/galbot/lizekai/RSI/codex-account-2/run.sh` 使用辅助 20x 账号继续当前任务。你承接监控、代码修正、仿真、结果审查和下一轮启动，不只是产出计划或总结。用户此前已明确允许编写代码并运行仿真，暂不上真机；这项授权覆盖旧通用规则中“只读取/审查”的角色限制。保持 gpt-6-astra、xhigh，禁止降级。不要建立其他通用子代理；仿真中的 Astra policy 继续通过已有 app-server harness 调用。

## 目标和硬约束

- 抓方块先成功10次、优化skill，再进入SIMPLE。该门槛已经完成，不需要重做：`artifacts/R018/audit_summary.json` 记录10次独立重置的审计成功，5次终态保持，15次物理尝试。438条记录中423条是旧额度重试造成的无物理记录，不能算尝试；错误已修。抓取skill v14及episode0437/0438可复用。
- 当前目标：SIMPLE推门至少10次成功；SIMPLE所有可用操作任务各至少1次成功。不能把回放、诊断、旧策略成绩、接口预检算成功。仍未完成，非必要不停止。
- 每次决策前先写三行：当前问题、总目标、不可重犯的错误。每次失败保存为什么失败、证据、排除的假设和下一项改变，不盲目死磕一个点。
- 新代码/日志/视频/缓存统一在RSI；不得破坏已有环境，尤其psi_deploy和.venv-psi；不安装或下载新资源，不读api.json或账号auth.json，不删产物。
- 超过60秒的命令在tmux中运行并tee日志。不要中止慢推理，必须等待完整turn/completed与skill_update。物理在推理时暂停，此方案不是RTC或真机验证。
- 用第二账号run.sh启动所有新模型进程，不能裸codex或API回退。用户已授权该账号，真实只读路由检查见`artifacts/R019/account-2-routing-check/limits.json`：ordinaryUsageAllowed=true、planType=pro、通用周期13%已用；这是调用前读数。不能自动用重置券；usageLimitExceeded立即停止自动重试并保存状态。
- supervisor可读host审计信息定位问题，但actor只能读当前RGB、机器人本体状态/几何、相机标定、自己的公开经验。不能把物体位置、接触真值、隐藏奖励、oracle动作喂给actor。没有人工示教，也没有pi0.5前置策略。
- model_38000关节顺序以随附接口为准：串行29关节，跨模块按名映射；不要重犯Isaac交错顺序误判。

## 首先接管已有进程，禁止重复启动

检查tmux和最新result.json；本交接文件撰写时：

1. `simple-apple-01-0915`：苹果放碗首轮仍运行，主账号旧进程，不热切换；已经使用共享核心、详细任务说明与选择记录，但没有后来补充的原生手指几何。等其物理执行、完整推理和修订结束再下一轮。
2. `simple-faucet-02-0915`：刚启动第二轮，使用第二账号、新混合skill、详细任务说明和原生手指几何。输出`artifacts/R019/faucet-campaign/episode-0002`，日志`artifacts/R019/faucet-campaign-02.log`。确认model_backend.json、app_server RPC thread/start应答和首个实际动作后再报告该路由已实际用于任务。
3. 推门episode0005已经完整结束，下一轮尚未启动；不要被仍保留的旧tmux名称误导。

截至交接：推门5次完整失败、0/10成功；水龙头1次完整失败、第二轮进行中；苹果首轮进行中、0次已审计成功。其他任务仍有工作，不能宣布全目标完成。

## 关键路径与运行方法

项目 `/home/galbot/lizekai/RSI`。先读`AGENTS.md`和`ITERATIONS.md`末尾R019记录，避免重复探索。

现有解释器：`/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python`。
现有环境变量：
`TMPDIR=/home/galbot/lizekai/RSI/artifacts/R018/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MUJOCO_GL=egl PYTHONPATH=/home/galbot/lizekai/RSI:/home/galbot/lizekai/Loco_manip/locomanip/src`。

推门单回合：`tools/learn_door_skill.py --pd-profile checkpoint --output artifacts/R019/door-campaign`。
其他SIMPLE单回合：`tools/learn_simple_task.py --env-id <已核实入口> --task-spec <详细任务json> --output <独立campaign>`。
每次命令只运行一个episode，必须审查结果、失败和修订后继续；不要以已启动代替完成。
水龙头入口`simple/G1WholebodyOpenFaucetTeleop-v0`，spec=`ref/tasks/simple-open-faucet.json`。
苹果入口`simple/G1WholebodyPickAndPlaceAppleTeleop-v0`，spec=`ref/tasks/simple-pick-place-apple.json`。

`tools/learn_grasp_skill.py:run_episode`已固定`codex-account-2/run.sh app-server --stdio`，无账号回退；结果与model_backend.json记录路由。现有账户隔离脚本一字未改。旧进程使用启动时已加载的代码，不会自动切换。

## 已完成的skill/harness修改

用户新要求：最大限度复用抓方块skill；探究共享skill与每任务skill的平衡；保存选择、反馈、总结和自我修改；开始SIMPLE前给详细任务指导。

- 共享核心`skills/loco-manip-core/SKILL.md`来自抓取v14：选择自身经验、核对当前观测、受限执行、验证、修订。不是固定坐标模板。主skill总上限831 words/6250字符/5357非空白。
- `rsi/skill_transfer.py`一次性组装共享核心和任务经验；保存原skill、哈希和来源manifest，不覆盖后续Astra修订。每任务独立memory/versions、experience.jsonl。
- `experience_select`在新SIMPLE回合首次动作前强制选择来源ID，记录理由/适配/未复用项，允许失效模式变化后重选。公共记录在rollout/skill_selection.jsonl。
- `skill_update`保存change_summary、task_specific/shared_candidate、所选来源和证据。共享候选只保存到任务memory/shared_candidates；未跨任务验证和抓取回归前不提升到全局核心。保存公开摘要而非私有思维链。
- 详细task-spec放workspace.json，给目标、对象语义、阶段指导、失败/完成条件和接口限制，无物体真值。是任务输入，不靠无限增长主skill。
- `finish_attempt`允许至少3次已完成动作后以证据和新假设结束停滞回合，不计成功，仍完整等待复盘。不因为推理慢而调用。
- 新增结束回合时的suggested_existing_evidence，并让非法证据报错点名路径；旧水龙头和首轮推门曾误引agent/rpc_calls，不能再让模型猜证据目录。
- `rsi/simple_hand_geometry.py`提供原生Dex3末节碰撞mesh在腕系的包围范围/链接原点，仅机器人几何；不同于抓方块胶囊。是范围，不是接触面/TCP。已通过几何坐标变换测试和原生水龙头模型核查；通用SIMPLE新回合启用，推门专用runner暂未启用。
- 全套此前87 tests+12 subtests通过；近期账号路由相关13项、手几何/host/recording7项、最后skill/memory/geometry16项通过。不要无变化重复跑全套。

共享/独立/混合结构优劣尚未测定。先分析实际来源选择、重复失败、动作/推理成本；待控制可用且SIMPLE有成功，再在相同控制器、任务描述、初始经验、重置条件、预算下比较，不能把不同PD与不同初态的结果作因果结论。

## 推门与控制器：已排除什么

推门是asset003由原CloseDoor改成的闭门向外推开变体；host的DoorPushEvaluator要求手接触、开30度、1秒、站立。不能混淆成原生CloseDoor benchmark成功。原生物理对象与记录保留；未teleport执行。

- ep1 native Sonic PD不匹配：62动作/240.04模拟秒，0门接触/0角度；腕上漂约0.6m，重复保持耗预算。已补主动失败结束。
- 无接触25mm对照：checkpoint PD大幅改善手腕残差，不能抬脚问题独立。正式ep2起用checkpoint；不再调回native。
- ep2/3加载脚抬升、common-forward、toe-up、踝roll/yaw均未实现步进，恢复原足部参考可跟踪。
- ep4双腕侧移有最大28.745mm相机移动但脚无离地；明确激活双腕位置也无帮助。7动作、17.24秒、主动停滞，v4保留全证据。
- ep5双腕位置+姿态：5动作/13.08秒；左腕原姿态难跟踪，换成实际姿态能到位不等于恢复原姿态，侧移仍不迈步。v5 SHA `9fc4cd0c5bf4737281a0a0fdd59160a10c8757dc4c026e18063b82b8cab8e9b6`，760words/5883chars。Astra下一候选是仅右腕横向协调，未验证；你需要判断是否仍值得试，不能无限换腕部小参数逃避行走接口问题。
- `foot-response-01`左右踝6/8cm均不离地；`input-response-01`固定真实状态下脚目标会改变腿关节输出，排除目标完全被mask/丢弃。
- 去除SIMPLE body 0.2Nm friction的独立反事实也不离地，不将零摩擦加入正式场景。旧抓取资产第一例也不离地（只跑成1例，收尾close错误已记录修复，不能冒称4例）。
- `foot-trajectory-audit.json`审计9条已有完整轨迹，增高峰值均<0.1mm，排除只看终点漏掉中途离地。
- `foot-timing-01`仅左踝8cm参考2s改0.5s，峰值增高0.19787mm，仍超时。未验证协调连续chunk，不能据此否定连续轨迹。
- 旧指定会话01a0a061-f7e1-75d3-9b79-9bc251c193b4的turn24/25揭示D1复制当前本体帧和D2复制未来帧。当前`ScaleTrackInferFn._infer_common`是真滚动，`LiveSim.tick`是真不同时间插值；未发现旧缺陷重现。不要再误判串行关节序。
- 当前actor只有一个路点，0.5–3s，执行超时额外2秒保持；34帧参考，采0/1/2/3/4/25，50Hz tracker/200Hz SIMPLE。连续协调轨迹是待验证的接口方向，不能把添加接口当成功。

## 水龙头/苹果/其他

水龙头ep1：74动作、240.20模拟秒、wall3238.53秒，无成功。45到位/28超时/1夹爪阶段；多种.20–.50闭合与方向探测未建立抓持，活动杆身份/转轴不确定。脚曾漂移83.8/40mm，后期位置保持较稳但因果未证。v1 SHA `8f8bee07ce7cd0657c77fbe5679d31b343eacb6a24805db0f529108748d1b2f1`，793words/6132chars；第一份修订因agent路径被拒，已自行纠正。第二轮新结构保存其原版本并供选择。

水龙头native要求绝对关节角>.7rad并奖励累计；原SIMPLE内部reward每step调用两次，保留此benchmark语义，不声称1秒保持。苹果native只检查苹果-碗接触且不接触手及累计，必须另审视觉是否真在碗内；MuJoCo原生对象材质白，已记录，勿冒称完整原始RGB外观。

`task-inventory.json`共91注册入口，19 native Sonic接口预检均可用；65其他G1变体及7非G1尚待兼容性判定，不能静默删除。`native-task-criteria.json`保存原生准则，继承类有些仍需追溯。逐任务先明确描述、验收、实际可用性，再模型尝试，不把预检当成功。

## 视频与远端

抓取最终视频：`artifacts/R018/campaign/episode-0438/video/episode.mp4`。
所有SIMPLE回合有MuJoCo episode.mp4和host robot_trace.jsonl。
ds4090已有SIMPLE和Isaac，无需下载。远端HOME=/home/lidanshi，SIMPLE=/home/lidanshi/lizekai/SIMPLE，staging=/home/lidanshi/lizekai/RSI/render-r019-0915。
`artifacts/R019/isaac-door-0001/episode_isaac.mp4`已生成取回：241帧、1fps、完整物理时长。这是MuJoCo保存状态的Isaac重渲染，不是Isaac物理试验，不增加成功。缺失桌面MDL走默认材质，其他几何/状态原样保留。复用`tools/render_simple_states.py`，不要重做已完成录像。

继续监控和推进，更新ITERATIONS.md。该交接不是完成报告。若真正遇到额度或基础设施阻塞，写明具体阻塞并保存可恢复状态；不要制造重复空episode。
