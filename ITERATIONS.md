# 视觉抓取迭代记录

本文件保存开发审查、失败证据和下一步决策；不是机器人 actor 的记忆输入。评测真值和开发布局不得通过此文件进入 actor。

## 当前状态

- 当前目标：R010 按 GPT-as-Policy 结构形成 ScaleBFM UMI-4 四点 skill；先让红块 seed task 的 HOLD、视觉和基础动作通过，再训练／接入 π0.5，最后迁移 SIMPLE 门任务。自主视觉抓取尚未运行。
- 进展：已实现具名四点 SE(3)、双 DEX3、direct/hybrid tool schema、回合记录、RGB capture 与项目 skill，27 项测试通过。原始 ONNX 的两次 UMI-4 HOLD 均超时：双踝误差小于 3.4mm，双腕约 2–3cm；头相机可见红块但较小，右腕相机严重自遮挡。π0.5 与 SIMPLE 尚未连接。
- 冻结条件：GPT-6 Astra、model_38000、RGB 环境观测＋合法本体信息、真实接触、自由站立、单手方块。
- 费用：额外 GPT/LLM/API 调用 0；本地 ScaleBFM 推理已执行；未读取 api.json；Codex CLI 状态确认 ChatGPT 登录。当前任务中的分析使用当前 Codex 会话。
- 执行分工：用户本轮明确授权“允许编写代码并运行仿真，暂不上真机”。后续同一范围内继续实施，无需反复确认；不得进入真机。

## 每轮规则

开始前明确：当前目标、目前进展、已有结论、不可重犯的坑、待证伪假设、预算与停止条件。

结束后记录：做了什么、证据位置、结果、失败的直接现象、已证实原因、尚未证实的解释、是否保留修改、下一步最小实验、模型调用数量。

- 区分基础设施失败、接口失败、动作选择失败、物理执行失败和结果判断失败。
- 每次只改一个可归因因素；至少需要新增证据才能重复同一实验。
- 同一假设经两次有信息量的验证仍无进展，暂停该分支，整理反例，改查其他依赖或报告缺失证据。两次是本项目开发节奏，不是统计结论。
- GT 泄漏、身体失稳、参考/时序契约不一致立即停止相应能力实验。
- 历史结论按来源复用；不重新搜索已解决的问题。失效路径记录正确替代路径。
- 成功也保存完整轨迹和适用范围；不能只保存成功回合。
- 允许开发期逐轮改进；测试期冻结代码、提示、示例选择规则，不跨测试回合写回经验。
- 长任务使用执行节点的 tmux 和文件日志；不改 psi_deploy 或 .venv-psi，不删除数据。超过 500MB 的新增数据放 /home/galbot/lizekai/data。
- 不默认调用付费 API；套餐方式不可用时记录阻塞，不自动切换 api.json。

## R000 — 2026-09-14 — 接口审计与坐标诊断

### 目标与实际完成

目标是选择可复用的底层路径，并排除将旧演示误当 VR-5 抓取基线的风险。

已完成：读取关联任务最新分工、现有 checkpoint 接口、locomanip 适配器与旧回放入口；读取真实 ONNX 签名；运行一次 CPU 秒级坐标诊断。没有机器人 rollout，没有模型推理请求，没有改其他仓库。

### 失败及思考

1. **过期路径读取失败**：`N_TRACK_ASSETS/runtime/model_38000_metadata.json` 不存在。原因是我沿用了错误路径。定向查找后定位到 `N_TRACK_ASSETS/runtime_mirror/runtime/model_38000_metadata.json`。已解决，后续不重复寻找。
2. **VR-5 坐标契约不符**：locomanip `ScaleTrackInferFn` 在 mode 含 pelvis 时使用 yaw-only anchor；model_38000 的配套说明要求完整 pelvis 旋转。对实际 `_build_policy_task` 方法做构造输入诊断：骨盆绕 Y 轴旋转 10°，右腕参考相对骨盆为 [0.5,0,0] 米。当前路径输出 [0.5,0,0]，完整旋转契约应为 [0.4924038765,0,0.0868240888]，差约 0.08715574275 米。在临时对象中仅将 `_full_anchor_quat=True` 后，误差为 1.17e-8 米。**这是坐标构造的数值复现，不是实际机器人跟踪误差，更不是抓取失败根因已经查明。** 未修改源文件。
3. **旧回放入口不适合作主基线**：`play_motion_track.py` 默认 UMI-4、其他 checkpoint，并启用额外手腕力补偿；它还承担回放/数据生成。只替换模型路径不能将其变为 GPT＋VR-5 视觉抓取。额外补偿是独立控制成分，不应将其效果全部算给 ScaleBFM；本轮没有判定其必然物理不合法。
4. **时间差异暂不判错**：locomanip 默认末项 25 步，旧镜像 wrapper 固定 33 步；接口文档允许远期 offset 5–33 步。问题在参考实际采样与 timestamp 是否一致，不是数值不同就错误。保留后续检查，不盲改。

### 已有结论

- 当前原始 ONNX 外部 policy_task 是 253 维，内部拼接 14 维 mode 才是 267；已读真实签名。
- 29 关节为串行顺序；跨接口必须按名称映射。旧镜像 metadata 在这一点与配套说明一致，但不因此认证整个镜像导出包。
- VR-5 必须显式选择骨盆、双腕、双踝；灵巧手另行控制。
- 不需要付费 API 来验证这些问题。
- 人类视频与接口 ICL 都仍是待检验增益，不能解释当前尚未建立的自主闭环。

### 后续修改与停止条件

下一轮 R001 只处理 model_38000 的局部适配和有效性检查：在 RSI 独立适配层中显式使用完整 anchor、具名关节映射和 VR-5，不修改其他 checkpoint 的全局默认。先保留本轮反例，再覆盖零倾角、正负 pitch/roll、wxyz 与 x/z 旋转表示、模式掩码及实际输出缩放。数值契约通过后才进行受限的自由站立和单腕小动作验证。

若执行分工仍是用户运行，将相同检查和运行回执要求交给用户；不自行启动。若允许助手实现仿真，再在 RSI 中实施。

并行可推进但不扩大部署：复用 Show-Harness 的动作表达边界；设计数值增量与有限动作共用的请求格式；整理 KAT 式观测—实际动作配对记录。暂不安装整套框架、不下载 HumanPlus、不训练、不上真机。

详细证据与入口见 [PRECHECK.md](PRECHECK.md)。

## R001 — 2026-09-14 — 专用适配、短时站立与单腕配对

### 当前目标和修改

目标：把 R000 数值反例落到 RSI 独立代码，并检验自由身体下的基础响应。不实现完整抓取技能、不新增模型调用。

`rsi/scalebfm.py` 复用 locomanip 的观测编码和具名关节映射，显式限定当前 checkpoint、VR-5、完整 anchor 和 5–33 范围内的远期参考。CPU ONNX 执行，无训练、无环境修改。

新发现：locomanip 通用 action scale 与历史 model_38000 sidecar 在腰和 wrist_pitch/yaw 不一致。先比对原始 PT：Downloads 和 runtime_mirror 的 SHA256 均为 `92196213078dda5a759714a658363831d403e3705fddc04b9abaca11b96377fd`，确认为相同原始 checkpoint；sidecar 的重建来源及转换代码可追溯到镜像 `g1_29dof.py`。本适配器使用该具名 scale/default，并显式使用该来源的 PD 参数。它仍是有出处的部署配置，不是本轮重新认证了训练全栈。

没有修改 locomanip 原代码，也未直接使用那个只固化 WholeBody-14 mode 的旧 scripted wrapper。该 wrapper 的转换代码 `convert_38000_to_torchscript.py` 创建了全 1 mode_vectors，不能把 mode_index=0 误解成 VR-5。

### 验证与结果

- `artifacts/R001/tests.log`：5 项 unittest 通过，0.836 秒。包含保留旧路径反例、独立 SciPy 旋转计算对照、正负 pitch/roll/yaw、x/z 旋转编码、具名映射/VR-5 掩码、非法模式/时间拒绝、scale 与本体初始化。未将其称为完整闭环语义认证。
- `stand-01`：5 秒物理仿真，墙钟约 0.956 秒；无物体、无固定根、无额外手腕补偿。最大倾斜 4.481°、最低骨盆 0.751887 米；末帧右腕参考误差 0.031745 米，骨盆平移漂移 0.026711 米。
- `wrist-01`：同一初态/参数/时长，只将右腕 world-X 参考在第 1–3 秒平滑增加 0.02 米；完成 5 秒，最大倾斜 4.481°、最低骨盆 0.749613 米。
- 配对终点实际变化 `[+0.018438,+0.003664,-0.005232]` 米，相对请求 `[0.02,0,0]` 的差为 0.006575 米；绝对腕部参考误差仍为 0.034763 米。
- `wrist-01/start.png`、`end.png`：从保存的 qpos 重渲染；人工可视检查已看到自由站立人形与手部。它们不是在线 RGB 流，更不是物体抓取录像。
- 所有实验有 ticks.jsonl、summary.json 和 robot_states.npz。保留失败与成功的同一输出结构。

### 失败记录与原因边界

1. tmux 首次启动失败：沙箱无法连接 `/tmp/tmux-1000/default`，仿真尚未开始。通过正式权限审查后相同命令启动成功。不是控制器问题，没有绕过 tmux 规则。
2. 短时探针未触发高度/倾斜停止条件，但 **未达到“精确到位”验收**：末端仍有厘米级绝对误差和跨轴耦合。已证实“参考前移导致实际前移”，未证实误差是恒定标定偏差，也未证明抓取精度充分。
3. 仿真快于真实时间，没有注入云端等待；因此不能声称真实时序、延迟鲁棒性或取消能力已验证。
4. 源码快照在运行后生成；两次启动间有 `MODEL_SHA256` 导入形式清理，无控制语义变更。后续实验需在启动前保存源码版本，避免仅有事后指纹。

### 保留什么、接下来如何改

保留专用适配和本轮数据。停止对同一右腕偏差盲目扫参，不写死补偿；这组配对响应可成为开发期接口经验候选，不能当专家抓取示范。

R002 切换到在线可观测性与工具边界：将合法 RGB/机器人状态打包为 observe，记录曝光/状态/动作时间；实现单请求、有界目标、真实到位/超时、取消；手指另测。先用脚本动作验证，无需 LLM。明确 TCP 标定后才把腕部接口称为 move_tcp。

之后做同权限下的物理抓取可行性检查，再进入数值动作 vs 有限方向动作，以及接口 ICL 对照。已有框架优先参考 Show-Harness 的原语/解释器和近期反馈，KAT 的观测—动作配对；RoboRSI/ASPIRE 的外部修订机制已体现在本日志流程中，尚未移植其运行时。

模型费用：本轮额外 GPT/LLM 推理调用 0，API 调用 0；本地 ONNX 推理属于机器人 tracker，不是云模型调用。

## R002 — 2026-09-14 — 在线接口、人工观察与重置故障

### 当前目标与复用的历史结论

目标：让 RGB、动作请求、实际到位和失败状态可见，验证手指确实响应；本轮不启动 GPT 抓取试错。

已读取任务「EXP8A P0F 故障定位 runtime parity及执行器」（01a0a061-f7e1-75d3-9b79-9bc251c193b4）。复用两项直接可测经验：历史窗口必须滚动，未来参考必须对应不同物理时间。新增测试调用实际 infer 路径，仅替代神经输出，核查最近三次 proprio/action 的顺序；未来参考用已知递增位置核查采样和 timestamp。不能用浮点 std>0 替代真实时序验证。继续遵守串行具名关节映射、VR-5 显式掩码、完整 anchor；不同 rot6D 编码不可直接交换六个元素。

边界勘误：R000/R001 曾沿接口文字写 5–33。现按历史任务定位并读取镜像训练源码 `runtime_mirror/runtime/ScaleBFM/ScaleTrack/source/scaletrack/scaletrack/tasks/tracking/mdp/commands.py` 第 220–221、806 行：randint(5,33) 上界排除，因此本地 guard 收紧为 5–32。默认 25 不变；这不证明旧部署使用 33 就必然失稳。原始历史文字保留，后续采用本勘误。

### 做了什么与证据

- `rsi/live.py`：自由机器人、固定桌面、自由方块和显式接触；observe 只打包 RGB/机器人信息，不放物体位姿。当前位置仍来自仿真机器人状态，标明 diagnostic；同进程 packet 白名单不是操作系统隔离。
- `move_wrist(observation_id, command_id, delta, duration)`：observation_id 为观测编号，command_id 为幂等请求编号，delta 为世界坐标三轴腕部增量（米，范数最多 3cm），duration 为参考过渡时间（秒，0.5–3）。目标锚定请求时的实际腕部，执行中不累计。参考结束且实际误差连续 5 tick 小于 1cm 才报告到位；额外 2 秒仍未到位则超时。它不是 TCP 或姿态到位接口。
- `cancel()` 固定当前参考，底层控制仍运行；`set_gripper(closure)` 的 closure 是 DEX3 机械闭合比例，0 为张开，0.5 为半闭合，尚无抓取接触标定。左右手按名称独立控制。
- `tools/live_viewer.py`：50Hz 控制、每秒 head_cam/right_wrist_cam 在线图像，记录曝光、处理时间、历史、动作状态、事件；启动前写源码 hash。窗口用正式权限审查访问 X11 和 tmux，没有关闭 sandbox。
- `headless-02`：8 秒/400 tick、8 组双相机图像；移动→取消、半闭合→张开脚本通过，无稳定性停止。右食指首关节约从 -0.0033rad 到 0.7834rad，再回到 0.00047rad，证明响应而非抓取。时钟延迟中位约 4.1ms、最大约 126.6ms，尚非严格实时保障。
- `viewer-01`：用户确认窗口/方块正常、机器人轻微抖动、桌面悬空。10–20 秒且无键盘命令的窗口内，腕部 XYZ 范围为 0.633/2.840/0.833mm；20ms 相邻腕位移 p95 为 0.248mm。范围含漂移，不能解释为纯振动幅度或抓取误差。
- `tests-03-before-fix.log`：12 项中两项按预期失败（offset=33 未拒绝、外部时间重置后仍推理）；`tests-04-after-fix.log`：修复后 12 项通过。
- `viewer-02`：补四条有碰撞的固定支撑腿，保留桌面高度和方块初态；重开 15 分钟有界人工窗口，启动约 30 秒时未触发停止。最终结束状态以该目录 summary 为准，不把运行中状态写成通过整轮。

### 失败与思考

1. `headless-01` 启动失败：嵌套 XML 的网格相对路径解析到错误位置。显式使用原场景 assets 的绝对 meshdir 后 headless-02 成功，旧失败产物保留。
2. 旧 viewer-01 墙钟 133.67 秒而仿真终点 64.20 秒。我一度误判为 GUI 严重拖慢，并停止窗口。逐 tick 复查发现墙钟约 69 秒处仿真时间四次回零，最大相邻墙钟间隔约 84ms；不能归因于一次 70 秒渲染阻塞。触发重置的具体按键当时未记录，不能指认用户按了哪个键。现在记录全部 raw_key，并在下一次推理前检查时间连续性；异常立即中止，不能使用旧历史续跑。该保护未覆盖所有 GUI 状态编辑，仍只用于诊断。
3. 旧 summary 的 time_limit 是异常退出标注 bug，真实终止为我发送 SIGINT。原始文件未覆盖，在 `viewer-01/review.json` 补正；新代码区分 interrupted/runtime_error。以正确取证修正自己的判断，不能重写旧日志掩盖问题。
4. 当前静止腕相机视野不利于对齐；head_cam 能看到方块。尚不能由一个姿态判定相机外参错误，也不因此先加感知模型。
5. 部分人工移动被 busy 拒绝，最后一个请求超时；不是所有按键都应立即抢占动作。旧 reset 后的轨迹不用于连续性能结论。现窗口可以用 X 取消，下一请求需等待前一请求结束。
6. 桌面此前是 world 固定单板，没有可见支撑；并非方块违反接触悬空。按用户反馈补腿是场景修正；它改变障碍几何，不能将新旧全部接触轨迹视为严格单变量控制比较。

### 已有结论和下一步

现在已有一个小型确定性执行 harness；memory 或小 VLM 不能替代参考生成、时序、到位判据和实际接触。Show-Harness 的有限动作/解释器边界、KAT 的观测—实际动作配对、RoboRSI/ASPIRE 的外部失败修订机制继续作为复用方向（来源见 PRECHECK.md），本轮没有安装整套框架或把这些名称当作已验证能力。

保留适配、接口测试、全部失败和人工数据。下一轮先解决 wrist→TCP 的几何与姿态定义、接近时相机可见性，并检验同权限人工小步能否完成接触/抬升；当前腕位置接口加机械闭合并不保证抓取可达。静止抖动先留基线，除非它阻断上述验收，不盲调增益、不写死位置补偿。随后才构建有限动作反馈的接口 ICL；人类视频作为任务关系/阶段提示的增益另做冻结对照。

仍需严格区分开发者可见场景配置与正式 actor 输入；当前会话不能作为无物体特权的冻结视觉评测者。额外 GPT/LLM 调用 0，API 调用 0，未上真机、未改受保护环境、未删除数据。

## R003 — 2026-09-14 — 用户指出左臂抖动，排除两个直接解释

### 目标、纠正与目前进展

用户确认：机器人自身左臂或左手明显抖动，桌腿正常，其他显示正常。R002 只检查右腕位移和跌倒阈值，遗漏了左臂运动质量；不能用右腕毫米级变化否定用户观察。暂停抓取推进，先定位。

viewer-02 已结束，summary 原因 external_sim_time_change，约 243.8 秒；raw_key 记录到时间回零前的 259，但不依此推断用户意图。重置保护生效，没有继续旧历史。前 240 秒无动作命令，可用于静止诊断。10–20、100–110、220–230 秒三个窗口左肘范围约 1.25、1.40、1.33°；左手指关节自身范围约千分之几度，当前证据更指向手臂带动手部，而非左手指开合振荡。

### 做了什么、失败与原因边界

新增 `tools/jitter_probe.py`，每次固定 20 秒物理仿真，启动前源码 hash，输出完整 50Hz 关节实际值/模型目标和逐物理步接触计数。无 GUI、无人工动作、无 GPT。每次墙钟约 4–6 秒，未达到长任务阈值。所有数据保留在 `artifacts/R003`。

1. `stationary-01`：原场景复现左肘波动。10–20 秒实际范围 1.249°，相邻 20ms 差值 RMS 0.162°，2Hz 以上谱峰 6.9Hz；模型左肘目标范围 4.132°、相邻差 RMS 0.936°，也有 6.9Hz 峰。左右 29 关节无力矩限幅命中，未检出左臂/手接触。发现右食指与桌面持续接触，说明此前“静止无额外接触”的隐含假设错误。接触计数为接触点次数，不等于接触持续步数。
2. `table-shift-01`：只将桌子/四腿/方块沿 world-X 平移 0.1m，保持机器人初态、参考、模型、增益不变。所有手桌接触消失，左肘范围 1.167°，相邻差 RMS 却升至 0.179°，谱峰 6.7Hz。右肘波动也增大。**消除接触未消除左臂抖动**；不再围绕桌子位置扫参。意外接触仍是后续场景布置需修正的问题，不能把原场景当无接触站立基线。
3. `physics-2ms-01`：在 table-shift-01 基础上，将物理步长 4ms 减到 2ms，每个物理步重新计算 PD，tracker 仍 50Hz。同一因素是物理/本地 PD 更新频率，不能声称只改变积分器而 PD 频率不变。左肘范围 1.462°、相邻差 RMS 0.184°，谱峰约 5.4Hz，未改善。单次确定性对照不能排除一切数值因素，但不支持采用此修改作为修复。

三次都未触发跌倒/非有限停止；这只说明完成采样，不是稳定性验收通过。频谱只是 10 秒窗口描述，非根因证据。模型目标与实际动作都波动，仍可能是模型—本体观测—动力学的闭环效应，不能单凭相关性认定模型权重有问题。

### 保留与下一步修改

保留诊断脚本和反例；未更改正式 `LiveSim` 场景位置、增益、checkpoint 或滤波器，也未重开一个未经改善的窗口宣称修好了。R002 的 12 项接口检查仍仅验证接口，本轮没有借此认证抖动问题。

下一轮检查静止参考可实现性：当前 5 点参考来自初始化 FK，而实际自由站立会沉降/偏移；先量化左右腕/骨盆/双踝的实际—参考误差，再做一次有出处的静止参考对照。需要同时记录目标、实际和姿态，防止把“降低响应”当稳定改善。若仍无进展，转查训练资产与当前 DEX3 资产的惯量/运动学差异；不继续盲扫 PD 或用 memory/小 VLM 掩盖底层问题。TCP 与视觉 ICL 等待该关卡恢复。

费用：额外 GPT/LLM 调用 0，API 调用 0；未上真机，未安装依赖或修改受保护环境，未删除任何数据。

## R004 — 2026-09-14 — 连续排查与参考伺服候选

### 目标与决策边界

用户要求“继续，非必要不停止”。本轮不因单次失败结束；不同假设有界验证，失败后切换依赖，不扫同一参数。目标是把左臂抖动与跟踪偏差一起评价，而非只优化一个 RMS 数值。所有新增 rollout 均为本地仿真，20 秒物理时间、约 4–6 秒墙钟；不调用 LLM/API。

### 已完成的对照与否决理由

详细数据位于 `artifacts/R004/<实验名>/summary.json` 与 trajectory.npz；每个实验有启动前 manifest。指标窗口通常为 10–20 秒；不同实验的目标位置不同，不应只比较绝对终点。约 5–7Hz 等频率为有限窗口谱峰，不是硬件故障频率认证。

- `initial-body-01` 补充原参考基线的全身位置/姿态记录，目的不是重复确认旧结论。无手桌接触基线：左肘相邻 20ms 角度差 RMS 0.179°，左腕位置误差 35.3mm、右腕 30.5mm，骨盆姿态误差 3.22°。
- `settled-01`：前 4–5 秒机器人 qpos 平均后做一次 FK，冻结该参考，之后不追逐实际状态。左肘逐帧 RMS 降至 0.090°，但骨盆姿态误差增至 4.72°，手腕总摆幅未同步改善。**否决作为正式默认**。该改动有启动参考跳变，不将它描述成连续轨迹生成器。
- `arm-hold-01`：第 5 秒后双臂目标固定为前一秒模型目标的均值，动作历史写实际执行目标。左肘 RMS 降至 0.045°，约下降 75%；说明持续变化的目标值得处理，但不能由此单独归因权重。**仅因果诊断，固定手臂不能用于抓取**。
- `arm-smooth-01`：80ms 时间常数的双臂低通，腿/腰不处理；左肘 RMS 降至 0.082°，但左腕 X 摆幅增至 11.2mm（原 2.8mm）。**否决**，不能用高频下降掩盖低频摆动。
- `implicit-pd-01`：相同增益改为 MuJoCo affine position actuator，使速度反馈进入隐式驱动处理。左肘 RMS 0.180°，未改善。训练源码使用 ImplicitActuatorCfg 并不证明 MuJoCo 此实现完全等效于 PhysX。**不采用**。
- `friction-01`：仅采用镜像 ScaleBridge 部署 XML 的 0.1Nm joint frictionloss（当前策略关节为 0）。左肘 RMS 0.176°，无实质改善。这个数值不是本用户真机标定；**不采用为修复**。
- `arm-rate-01`：只限制双臂关节目标变化速度为 0.5rad/s，动作历史同步实际下发值。左腕 X 摆幅增至 8.1mm，**否决，不继续扫限速参数**，因此没有扩大该候选的动作测试。

### 资产差异与重力补偿分支

已确认当前 gyro_pelvis 绑定 pelvis site，没有把 torso gyro 当 pelvis 使用。镜像基础 XML 与当前 DEX3 XML 的左腕 yaw link 平移相差 5mm；左腕 roll 子树质量分别约 0.824kg、1.551kg，不能把当前带手资产视作完全相同动力学。训练配置指向 USD；本轮 XML 审计不等于完整认证实际训练 USD。

`reference-asset-01` 与 `dex3-asset-01` 用同一 Model38000 和 standing_probe，均无桌面物体，运行 20 秒。基础 XML 只在 RSI 产物内复制、改绝对 meshdir、gyro 名称别名和 integrator，未修改原资产。左肘逐帧 RMS 为 0.030° vs 0.179°，基础资产仍有较大慢漂移。因此资产差异与快速波动相关，但这组比较同时包含几何/质量/摩擦等差别，**不能单独归因手的质量**。reference_scene.xml 不是抓取场景。

`payload-comp-01` 用两套机器人模型的静态 qfrc_bias 之差计算双臂附加载荷重力力矩，保持当前手的真实质量。左肘 RMS 0.070°，但左腕位置误差增至 39.8mm。**仅保留诊断，不加入运行默认**。它是附加控制力矩，不属于原始 tracker；不能以此宣称已完成硬件可用修复。

### 可复用方法与采用的候选

重新定向读取已有 locomanip 的 `HandForceCompensation` 和 `GraspRefServo`，没有重新开展外网综述。前者通过 Jᵀ 将腕部误差变成附加力矩；后者积分“原始参考－实际腕位”来修正 tracker 参考。本轮选择后者的思路，避开原数据生成器的物体位置、阶段真值和 15cm 默认大修正范围。

RSI 新增 `rsi/reference_servo.py`：50Hz、每步 gain=0.08、每腕修正范数上限 5cm。输入只有未来腕位参考与机器人实际腕位；原目标、其他三点和姿态参考不改；实际下发参考另行记录。此组件是额外 harness，不是 frozen model_38000 自带能力。积分上限已出现饱和，未知大范围动作和接触条件下是否充分，不能直接放大。

- `reference-servo-01` 静止：左/右腕位置平均误差约 13.1/8.9mm，低于原 35.3/30.5mm；但腕姿态误差约 5.56/4.01°，左肘总角度范围仍达 1.73°。**位置改善，未宣布左臂稳定通过**。
- `raw-move-01`：第 10 秒从观测实际位置发出 world-X +2cm、2 秒参考过渡；4 秒期限内未到位，最后记录误差 14.0mm。
- `servo-move-01`：同样的观测锚定请求规则，参考伺服达到原用户目标，报告到位时误差 4.53mm；均为各自当前实际位置锚定，不能说两次用了完全相同的世界终点。
- `servo-integrated-01`：从原型迁入 LiveSim 后，重跑该有信息量的集成检查，命令结果与原型复现一致，误差 4.53mm。保留旧原型产物。
- `servo-tests-before.log` 保存新增组件尚不存在的红灯；`servo-tests-after.log` 15 项通过，覆盖非法/非有限观测不污染状态、5cm 修正边界、原目标不被修改、未来帧增量保留、新会话清零及原 12 项接口检查。新功能红灯是模块缺失，不伪称复现了旧实现的某个非法输入 bug。

LiveSim 与窗口通过显式 reference_servo 开关选择，默认原路径仍保留；没有采用上面否决的低通、限速、载荷力矩或摩擦修改。窗口参数 `--reference-servo --table-offset-x 0.1`，桌子和方块一起移远 10cm，避免静止手桌接触。用户已获知这是候选。`viewer-01` 通过 tmux 开启，15 分钟上限；已确认 X11 窗口显示，人工反馈待返回。窗口关闭/重置不会自动宣称完成，最终以 summary 为准。

### 尚未解决与连续推进

左臂可见抖动是否可接受仍待人工复核；位置伺服并未解决全部姿态误差。继续做 TCP/闭合几何检查，不调用 GPT 反复试错；若人工复核失败，保留位置伺服的独立结果，不能把它包装成抖动修复。后续至少覆盖不同方向小动作、取消后保持和接触前姿态。

本轮早期诊断保存的是源码 hash，尚无每个版本的完整快照；不得声称仅凭 hash 即可重建全部旧版本。后续 probe/viewer 已改为启动前同时保存本地源码副本。当前已运行 viewer 的 manifest 对应修改前版本，不追写伪造快照。所有失败产物保留。

源路径补正：配置目录为 `config/g1_29dof/`，不是 `config/g1/`；第一次定向读取旧路径失败后已纠正，不再重复搜索。额外 LLM/API 调用 0，无真机操作，无环境安装或数据删除。


## R004 人工验收更新 — 候选否决

用户反馈“现在左右手都开始抖动”。因此参考伺服作为抖动修复被否决，不能沿用前文“人工反馈待返回”的历史状态。viewer-01 已由 SIGINT 停止，summary 记录 interrupted，约 235.58 秒仿真；未运行自主抓取。候选源码和轨迹保留，默认关闭。位置误差改善不能覆盖人工运动质量失败。

## R005 — TCP 几何检查中止

`tools/tcp_geometry_probe.py` 首次运行假定存在 `right_hand_thumb_2_pad_collision`，实际资产不存在该 geom（存在 thumb collision，但没有该 pad 名称），所以 `artifacts/R005/geometry-01` 未生成有效结果。原因是未经核实的资产命名假设；没有得到 TCP 标定或抓取结论。用户随后明确要求优先定位双臂抖动，故暂停此分支，不同时修多个问题。

## R006 — 2026-09-14 — 双臂抖动的同步信号链与 FSQ 单因素诊断

### 目标、方法和命令含义

目标是判断抖动出现在上层参考、模型输入构造、模型内部、输出解码还是物理执行。复用现有 locomanip 的输入构造、同 checkpoint 的 eager 架构与冻结 PT 权重做数值可验证的内部探针；没有调用 GPT，没有引入物体特权信息，也没有训练小 VLM 或构造 ICL memory。此时 memory 不能修复 50Hz 控制闭环。

基线不是 GPT 在反复发移动命令，而是 `HOLD_INITIAL_WORLD_REFERENCE`：双腕、双踝、骨盆五点的世界位姿参考固定，右手闭合请求为 0。完整链条是：

1. 世界参考：固定位置/姿态，或一次 `move_wrist(observation_id, command_id, delta, duration)`。delta 是世界坐标系中的右腕位移（米），duration 是参考过渡秒数；此接口尚不是经标定的夹爪 TCP。
2. Harness 采样未来参考：tracker 50Hz，取第 0/1/2/3/4/25 帧。可选参考伺服额外修改双腕位置，本轮基线关闭。
3. 观测构造：`policy` 为 3 帧本体历史；`policy_task` 外部每帧 253 维、共 6 帧，含参考相对骨盆的位姿、相对实际身体的误差和时间。VR5 mask/mode 使五点生效。内部拼接 mode 后为 267 维，不能把 267 当外部 ONNX task 维数。
4. 即使世界参考固定，机器人实际姿态变化仍会使相对坐标及误差变化；task encoder 把它编码成 32 维 latent，再经 FSQ（有限标量量化）限制范围并取整成离散码。
5. decoder 结合 code、本体历史和动作历史输出 29 维归一化动作 `a`。`q_target = q_default + action_scale * a`，按关节名映射，串行关节序，不套 IsaacLab BFS 假设。
6. 每 4ms 的本地 PD：`tau = clip(kp*(q_target-q)-kd*dq, torque_limits)`。tau 为力矩，q/dq 为实际角度/角速度，kp/kd 为比例/阻尼增益。执行后的实际状态再次进入第 3 步。

### 同步核对结果

`tools/chain_probe.py` 记录每个 20ms 控制帧的原参考、修正参考、实际身体状态、实际发送的所有模型输入、原始动作、解码目标，以及每个 4ms 物理步的 PD 输入、未限幅力矩、实际发送力矩和执行后关节值。`raw-chain-02` 与 `servo-chain-01` 各 1000 控制帧、5000 物理帧；本地单轮约 4–6 秒墙钟。

- 原始 HOLD 世界参考变化为 0，未经伺服的 tracker 世界参考变化也为 0。此前伺服候选的实际参考变化最大约 49.5mm，不能再把它描述成与原始输入相同。
- 原始动作→关节目标解码误差 0；PD 计算→实际下发误差 0；动作历史最新帧→前一步输出误差 0；物理步末状态→控制帧记录误差 0。本体关节输入与 PD 实际关节的浮点误差约 3e-8rad。
- 独立 SciPy 位姿重算最大误差：位置约 1.1e-7m、姿态 6D 特征约 2.3e-7、投影重力约 3e-8。结果在 `independent_geometry_check.json`。未发现本次帧变换/四元数计算错误，不等于证明所有部署约定都正确。
- 原始 ONNX 离线重放误差约 1.4e-6。冻结全部模型输入后的输出变化为 0，排除本次模型随机输出噪声假设。
- 离线单步替换仅令 task 变化，左肘模型目标相邻 20ms 差值 RMS 为 1.063°（全输入变化 1.137°），右肘为 0.854°（全输入 0.843°）。腕部误差特征贡献显著，尤其姿态误差。非线性结果不能相加，也不是因果贡献百分比。

### FSQ 检查前先纠正重建误差

镜像 `scripts/exp8ap/scalebfm_eager.py` 使用 `(levels-1)*(1-eps)/2` 的 bound，与实际 ONNX 不一致，最大动作误差约 0.074。用现有 `locomanip/bfm/two_stage.py` 的 `1+eps`（eps=.001）仅替换检查模型中无参数 FSQ 后，499 个真实输入上量化输出与 ONNX 最大误差降到 1.67e-6（servo 数据约 2.03e-6）。**原本运行的 ONNX 已是匹配的公式；没有修原始 ONNX，也没有改权重。** 旧 analysis.json 的 unverified 结果保留，后续 fsq_audit.json 才是经 parity 校验的检查结果。

原始静止轨迹中约 97.8% 相邻帧的离散 code 发生变化，平均每帧 32 个维度中的 3.85 个跳变；伺服候选平均 5.20 个维度跳变。仅凭相关性不足以定因，故继续以下单因素对照。

### 失败分支与切换理由

- `freeze-task-01`：10 秒起冻结全部 task，约 10.90 秒触发失稳停止。不能部署陈旧反馈。
- `freeze-wrist-rotation-01`：仅冻结腕姿态误差，没有消除实际抖动。
- `freeze-wrists-01`：冻结两腕 task 特征，模型目标跳变下降，但实际双臂出现明显漂移。实际关节逐帧差值包含漂移，不能全部称为高频抖动。这些都只用于因果诊断，不作为修复。
- `hysteresis-01`：FSQ 在 0.1 bin 滞回区内保持原码。码跳变维度从每帧 3.73 降至 1.19，但左/右肘实际逐帧 RMS 从 0.184°/0.116° 增至 0.195°/0.156°，腕部总摆幅增大。**否决，少跳码不自动等于更好控制，不继续扫滞回参数。**
- `inertia-damping-01`：按当前 DEX3 与基础资产质量矩阵对角线的平方根比值调整双臂 kd，左/右肘降至约 0.145°/0.077°，位置偏差仍约 35/31mm。只属部分改善；对角近似不是完整耦合动力学标定，不采用默认。

### 决定性单因素结果：只取消 FSQ 取整

离线冻结本体/动作历史、只让 task 变化时，量化与去取整的左肘目标逐帧 RMS 为 1.063°→0.0658°，右肘 0.854°→0.0542°，说明取整在该输入邻域显著放大输出跳变。

接着用同一份权重、同一物理资产/PD、实时更新全部输入，进行闭环对照：`torch-raw-01` 与 `continuous-diagnostic-01`。唯一处理差异是 `round(bounded)/(levels//2)` 改为 `bounded/(levels//2)`。取 10–20 秒静止窗口：

- 左肘实际逐帧 RMS：0.183665°→0.0000795°。
- 右肘实际逐帧 RMS：0.115774°→0.0002439°。
- 连续分支左右腕平均位置误差仍约 34.3mm/28.3mm，20 秒未失稳；跟踪偏差未解决。

结论：**FSQ 硬量化与实际反馈构成的闭环，是当前场景双臂快速抖动的主要产生/放大环节。** 资产动力学与初始参考不可实现性仍可能影响闭环运行点，不能声称 FSQ 在所有场景都有缺陷，或已经找到了训练/导出的设计错误。

`continuous-move-01` 在第 10 秒，以观测右腕为锚点发 world-X +2cm、2 秒过渡。首帧量化重建与 ONNX parity 为 1.09e-6；20 秒未失稳。右腕至末帧实际位移约 [20.88,15.10,4.02]mm；在 4 秒期限处到位误差 15.77mm，状态 timed_out，最终误差约 15.65mm。因此手臂并未被锁住，但有横向耦合和位置偏差，不能通过动作验收。移动期间逐帧角度差混有主动运动，不能与静止抖动 RMS 混算。

### 当前保留、窗口与下一步

新增 `rsi/diagnostic_latent.py` 作为显式诊断后端，每次新会话首帧自动用量化重建与原始 ONNX 比对，误差超过 1e-4 则拒绝继续。`tools/live_viewer.py --diagnostic-continuous-latent` 标记为 `DIAGNOSTIC_OFF_GRID_CONTINUOUS_LATENT`，禁止与参考伺服叠加；默认仍为原始 ONNX。连续码偏离原离散接口，**不是 model_38000 原始语义，也未获硬件验证**。

`viewer-continuous-01` 通过 tmux 会话 `rsi-r006-view-0914` 启动，15 分钟上限、完整日志、已核实 MuJoCo 窗口存在，人工稳定性反馈待返回。窗口使用 +0.1m 桌面偏移避免意外接触，无自主抓取。

下一步先以人工观察核对静止结果，再检查动作方向耦合和位置偏差。保持原始量化基线；若保持原始离散接口是硬要求，应围绕可实现参考/反馈输入及资产一致性继续，而不能默默采用连续分支。此诊断不需要小 VLM 或 ICL；视觉 harness 之后应负责有界目标、进度判断和误差恢复，不能直接负责高频稳定。

### 记录质量与环境失败

- raw-chain-01 由于 NumPy tuple 索引误用导致记录器失败，已改为 list 索引；旧 summary.reason=null 不代表完成。保留原始失败目录并补 review.json。
- 旧 freeze_comparison.json 包含失稳后不足窗口的统计/NaN，已用 freeze_comparison_v2.json 明确排除不完整窗口；保留旧件，不当作有效对照。
- 正确几何审计路径是 `artifacts/R006/independent_geometry_check.json`，不在 raw-chain-02 内。读取一次错误路径后已纠正。
- 本地运行环境无 pytest；现有测试使用 unittest，应直接运行 unittest，不安装依赖。接口测试日志 `interface-tests.log` 只检验接口，不认证闭环稳定。
- 绘图时现有 psi_deploy 的 NumPy/Matplotlib ABI 不兼容，仅读取失败，未安装或修改包。改用已有 mjlab 环境生成静态科研图；运行模型环境也未改动。
- 新探针保存源码快照与 hash；旧轮仅 hash 的局限保留。新版窗口额外保存诊断 helper、外部 eager 源码与 FSQ 源码。没有事后伪造启动时快照。

证据图：`artifacts/R006/signal_chain.png`、`signal_chain_right.png`、`freeze_feedback.png`、`freeze_feedback_right.png`、`quantizer_diagnostic.png`。所有失败轨迹保留。额外 GPT/LLM/API 调用 0，无真机操作，无环境改包，无删除数据。


### R006 持续运行回执（2026-09-15）

现有 unittest 15 项通过，日志 `artifacts/R006/interface-tests.log`；未安装 pytest。连续 latent 窗口最新审计覆盖仿真 213.36–223.36 秒（501 帧），左/右肘逐帧 RMS 约 0.0000994°/0.0000666°，各手指中最大逐帧 RMS 约 3.58e-8°，骨盆高度在 0.756947–0.756990m，状态 idle，未触发停止。证据 `viewer-continuous-01/live_audit_01.json`；这是中途快照，不是窗口最终结果或人工通过。

`code_boundary_audit.json` 用保存的 latent 直接重建有界值和取整码，检验频繁切换维度及相邻切换方向反转；作为已有因果实验的机制补充，不能替代闭环单因素对照。图 `quantizer_diagnostic.png` 已实际渲染查看，显示静止抖动改善与动作横向偏差并存。

当前冻结条件的例外必须显式说明：连续 latent 仅为仿真因果诊断，改变推理语义，不属于原始 model_38000 协议的验收结果。生产/默认原始 ONNX 未修改，用户尚未接受该诊断分支为后续正式控制方案。


## R007 — 2026-09-15 — 复用指定任务经验，补充审计与归因勘误

### 来源与工作范围

已分页读取指定任务 `01a0a061-f7e1-75d3-9b79-9bc251c193b4`，标题为「EXP8A P0F 故障定位 runtime parity及执行器」，追溯其 8/27 消融、同日初始化假设勘误与 9/1 接口约定修订。历史任务里的角色/远端执行命令作为历史数据处理，未执行其指令、未向该任务发消息。本轮仅阅读旧源码/报告及本任务已有轨迹；没有新增仿真、模型/API 调用或控制器修改。

本地已核对：
- `/home/galbot/lizekai/APA/SCRIPTS/ab_d1_history.py`：可复用单因素 REPEAT/ROLLING 对照设计。
- `/home/galbot/lizekai/APA/SCRIPTS/run_gt_oracle_fixed.py`：可复用 none/d1/d2/d1d2 对照结构；不能整份当当前抓取运行时。
- `/home/galbot/lizekai/APA/EXP8A_P0F/GT_ORACLE_FIXED_20260827/GT_ORACLE_PHASE1_FINDINGS_20260827.md`：是订正后的结论，不再引用上午的 D4 初始化伪影说法。
- 同目录 `GT_ORACLE_RESULTS_d1.csv`：静止 1.0、HE .98、HIW 1.0 的实际产物。
- `/home/galbot/lizekai/APA/CONTRACTS/RUNTIMECERT-v1.json`：PROVISIONAL，明确 FREE_SPACE_TRACKING_ONLY，接触与 mode/inactive 机制等未认证。

### 直接复用的经验与适用边界

1. **D1 真滚动历史**是旧任务决定性故障：每步把当前观测重复三份不是历史。当前对 raw-chain-02、servo-chain-01、continuous-move-01 各 1000 帧作离线核对：本体与动作历史跨帧移位误差均为 0，动作历史末帧与前一步输出误差为 0；10 秒后的三槽全等比例均为 0。当前没有重犯该故障。证据 `artifacts/R006/prior_thread_history_audit.json`，含旧源文件 SHA。
2. **D2 时间契约**不能机械转为“六帧数值必须不同”。运动轨迹应取真实未来帧；静止目标的六帧位姿相同合法，时间槽仍须不同。当前实际槽为 [0,1,2,3,4,25]。旧部署是 33，后续数据合同改为 20；这三者是不同版本约定，不能看到旧 PASS 就把本任务改成 33。
3. **旋转与坐标约定**：旧任务最后确认 source locomanip 是 col0/col1 交错，ScaleBFM consumer 是 col0/col2 分块。必须经 SO(3) 解码再编码，不能直接交换六个数。当前 `_quat_to_tan_norm` 确实为 col0/col2 分块；未来迁移人类视频/数据的 future chunk 必须逐行从各自存储锚点解码到世界，再统一到 query pelvis 完整 SE(3)，不能单个 nav 锚点解码整段。
4. **旧成功率不能移植成抓取精度**：旧 oracle 是 4 秒、root z<0.4 才记跌倒、最后平均 body error<=0.5m 即判成功。CSV 静止 body_tracking=.1405m、joint_tracking=.154rad。STATIC 分支重复同一初态，代码没有逐次初态扰动，不能把 N=50 当成 50 种独立站姿验证。旧实验证明其门槛下的 D1 修复效果，没有证明微抖/长期稳定/腕部厘米级到位。
5. **不要直接替换为旧 TorchScript**：旧源码 FSQ 使用 1-eps，当前原始 ONNX 的匹配重建是 1+eps。旧证书的 parity 参照与外部输入封装也不同，不能凭同名当作同一运行链。旧脚本由 q29 FK 构造参考，不等价于本任务视觉目标＋世界五点参考。

### 对 R006 结论的限定

保留“仅去掉取整大幅减小当前闭环抖动”的因果证据，但其解释限于**当前输入构造、资产和参考运行点下，硬量化是主要抖动放大环节**。不能升级为“FSQ 设计错误”“model_38000 本身不可用”或“应正式移除量化”。下一轮仍保留原始 ONNX 路线，continuous 仅显式诊断；旧任务的教训要求优先核清 wrapper 与参考语义。

### 新发现：上轮方向耦合归因过早，现订正

R006 的 `move_wrist` 语义是：目标 = 当前观测实际腕位 + delta；轨迹起点 = 旧 nominal reference。当静止已经有厘米级 tracking bias，这两个锚点不同。

`continuous-move-01` 在发令时：
- 相对实际腕位的用户请求：[20,0,0]mm。
- 旧 nominal reference 到新目标的变化：[23.236,27.172,6.851]mm。
- 实际腕位末帧位移：[20.880,15.103,4.017]mm。
- 相对真正目标的末帧误差向量：[0.880,15.103,4.017]mm，到位超时仍然有效。

因此**这不是纯 X 的 tracker 参考扰动**。前文及上轮回复中“存在方向耦合”的表述过早，撤回其因果解释，保留位置误差与超时事实。Y/Z 参考也发生变化，不能把实际 Y 移动全归于 X→Y 耦合。证据 `artifacts/R006/movement_anchor_audit.json`。图本身显示的是相对实际腕位命令与实测位移，数据不作废，但解释必须附上述限制。

### 下一轮最小实验

先做参考语义的成对诊断，禁一次改多层：
1. 原始 ONNX、无额外伺服，保持 Y/Z nominal reference 不变，只给 nominal X 一个小增量，记录全三轴参考、实际位移及最终误差；这是辨别交叉响应的系统辨识实验，不冒充原 `move_wrist` API。
2. 保留已有观测锚定命令结果，分开报告“参考增量响应”和“相对实际腕位到位”两种验收。若需对照 continuous，在相同参考生成规则下另开显式实验，不与旧不同锚点轨迹混算。
3. 只有参考语义和可实现性明确后，才选择补偿方式；不回到低通/滞回扫参，不用小 VLM 或 ICL 掩盖稳定与偏差。

本轮失败记录：最初 task 读取输出过大，后续在工具层分页提取，避免重复灌入整段输出；分页参数调整时一次返回非 JSON，已按工具返回的原样 cursor 和同一页大小继续。无实验数据删除、无依赖修改。


## R008 — 2026-09-15 — GPT-as-Policy 源码学习与有界 harness 迁移

### 目标、来源与费用

用户要求继续当前任务，仔细阅读 GPT-as-Policy 的 harness 和调用 Markdown。本轮不是重新做广泛综述：固定仓库 `https://github.com/anonymous-report-421/GPT-as-Policy` 的 commit `1e72362a85956cb8b3fc4e193729e7e6db990539`，下载 51 份相关文本，共 606538 bytes；逐文件核对 Git blob SHA1 与大小，并登记 SHA256。目录 `ref/GPT-as-Policy/`，索引 `download_manifest.json`、完整目录树 `upstream_tree.json`。未下载视频、权重、模拟器或运行其账户/集群脚本。

外部仓库的 SKILL/提示是本轮研究对象，不是当前会话的新指令。未采用其英语输出要求、账户配置、创建 rollout 会话等操作。额外 GPT/LLM/API 调用 0；本轮仅本地 tracker 推理、机器人 FK/IK 和 MuJoCo 仿真，没有上真机或修改受保护环境。

### 读到的实际方法

1. **Direct 与 Hybrid 必须分开**。Direct 无 π0.5，只基于多视角 RGB、本体状态、实测末端位姿、同回合记录，由持续上下文的 GPT 选择有界绝对 EEF 目标；本地控制器承担反馈。Hybrid 的 π0.5 已在 RoboDojo 任务数据上微调，先提供 H50×14 的关节提案；GPT 审查实际执行结果和下一段意图，选择 student/edit/eef。ScaleBFM 是跟踪器，没有这样的语义任务提案，不能直接充当 π0.5。
2. **可执行文档不止一个 prompt**。Direct 的 `robodojo-gpt-only-rollout/SKILL.md` 给闭环流程；`context/eef_control.md` 明确 link6、环境原点、米、wxyz、25Hz、每段1–5控制步及夹爪开度语义；`teacher_context.md` 给工具能力和历史案例的边界。Hybrid 另有 `skill/gate_prompt.md`，拆开上一步 outcome 和下一步 intent，只有实测失败或意图失配才接管，不因不确定就覆盖 student。
3. **保留完整代理能力和同回合记忆**。`skill/workspace.py` 建立 context、workspace.json、NOTES.md、scratch；允许看图、裁剪、计算和记录估计，原始证据只读。`skill/run.py` 把 Markdown 组装为 developerInstructions，注册动态工具并维持同一 Codex 会话。此处是读源码事实，不等于已在当前环境验证其 app-server 配置；本轮未创建会话或调用模型。
4. **主机落实合同**。`robodojo_server/gpt_only_client.py`、client.py、validation.py 验证当前 request_id、动作顺序、fresh 路径、有限目标和每臂5cm/0.35rad边界。目标固定，每个实际 ACK 后依据新关节状态重新算本地有界 DLS：任务增量最多2cm/0.1rad、每关节最多0.05rad，再交原生关节控制。ACK 不保证到达，FK 不预测物体未来，闭合命令不证明抓住。
5. **仿真时钟与真机不同**。session 的动作服务调用 env.take_action/env.step 推进物理，策略分析之间没有该路径的连续控制步。不能把这种步进式交互原样用于自由站立真机；当前 RSI 的 50Hz tracker / 250Hz PD 必须持续运行，GPT 不能阻塞它们。当前 move_wrist 的 0.5秒观测有效期也不能直接兼容数秒模型推理，后续异步服务须明确执行前的新观测复核，不能简单放宽时间或悄悄重新锚定目标。

### 效果证据应如何解释

README 报告 RoboDojo 50 个选定案例：Direct 13/50=26%，Hybrid 24/50=48%；Hybrid GPT 修正步占14.4%。Direct 平均分37.81只基于48个有 native score 的回合，成功率分母仍50。公开官方模型参照是重新加权结果，非同seed复跑。

`public_results/data.json` 的 RoboLab 附表：Direct49/50、Hybrid46/50、历史π0.5 18/50；notes明确含保留历史结果、授权重试、初态不严格配对，最后两个 Direct BlocksInBin 重试用500 decisions而非180。原库将其标为选定 slots 的描述性结果，非统一预算、全新、单次配对benchmark。成功例对方法可行性很有价值，但不能无条件外推至 G1/ScaleBFM。

RoboLab 的 eef_control.md 还明确给出 Panda/Robotiq base_link 到 nominal pad 的 +0.1311m local-X，并举“请求4.85cm，五步实际只走2.58cm”的反例。X5 文件明确禁止套用此偏移。本任务同样不能把 G1 wrist 当 TCP，也不能照搬 X5 opening=0闭/1开的约定。

### 已落地：可审查的动作回执与 Markdown

`rsi/live.py` 的观测补充 wrist_reference_world_m 和 measured-reference 的 wrist_tracking_error_world_m；移动回执补充 frame、controlled_link、观测实际锚点、参考起点、用户位移与参考实际变化。没有改变原 move_wrist 的目标语义或默认控制器。

`tests/test_live.py` 新检查人为制造2cm参考偏差，要求回执区分用户1cm X位移和参考[1cm X,2cm Y]变化。`anchor-test-before.log` 因缺字段失败，修改后 `anchor-tests-after.log` 16项全部通过。它们验证合同，不认证运动精度或抓取。

新增 `actor_context/POLICY_PROMPT.md`、ROBOT_CONTRACT.md、EPISODE_NOTES_TEMPLATE.md，明确状态为**待独立策略服务接入的提示候选**，不是已注册工具或已跑通 actor。仅描述当前实际支持的腕部位置/机械闭合/取消，明确未支持旋转请求、TCP抓取标定、异步长期思考。模板不灌入物体真值或本任务实验坐标。这里的 memory 是同回合、带证据的工作记忆；不是先训一个小 VLM，也不是已完成 humanplus ICL。

### 六组纯单轴实验：把参考响应与观测锚定请求分开

`tools/chain_probe.py --reference-step x|y|z` 在第10秒将 nominal reference 单独增加20mm，2秒平滑过渡，另外两个轴与其他四点参考保持不变。它是系统辨识诊断，不冒充 move_wrist 请求。每组20秒物理时间，约3–5秒墙钟，全部完成、未失稳。比较8–10秒与18–20秒平均腕位：

- 原始 ONNX：X参考20mm→实际[20.246,3.336,-4.472]mm；Y→[0.970,5.772,1.218]mm；Z→[0.465,-9.076,18.622]mm。
- 连续诊断：X→[17.229,2.393,-1.562]mm；Y→[1.399,10.074,0.033]mm；Z→[0.073,-4.227,16.171]mm。

记录：`artifacts/R008/reference-{x,y,z}-{onnx,continuous}`、reference_step_analysis.json 和 reference_steps.png。静止偏差不等于增量响应误差；这里仅为单姿态正向有限扰动，包含有限窗口漂移，不能直接当成全局 Jacobian。量化移除后 Y 响应不足仍存在，说明精度问题不能都归结于量化抖动。

### 机器人几何可达检查

`tools/wrist_feasibility_probe.py` 读取上述保存轨迹，将机器人根位姿、29关节按名恢复到无任务物块/桌子的机器人模型，初始腕位 FK 与保存值差为0。只改变右臂7关节，固定根、腿、左臂；有界 DLS 每步任务2cm/0.1rad、关节0.05rad以内，最多100次，**没有 mj_step 或关节下发**。

六个位置+姿态目标都在4–9次迭代收敛，最终位置残差0.25–0.45mm，姿态残差小于0.00003rad。仅说明存在局部运动学解，不验证平衡、碰撞、动态跟踪或物体接触。证据 wrist_feasibility.json。这排除了“这些目标右臂运动学上根本够不到”的解释，但没有证明 BFM 应当无误差实现它们。

### 参考适配：保留原始 ONNX 的有界对照

从原始 ONNX 三组实测响应构建局部3×3增量矩阵，条件数约4.13。只在 probe 的显式 `--reference-adapter --move` 分支使用：用户绝对目标仍为原观测实际腕位+delta，tracker 的轨迹终点则是旧reference+矩阵逆映射后的参考增量。范数超过3cm即拒绝，不扩大边界；无新PD、无双臂伺服、无量化修改。不是低层IK或已可部署的通用控制器。

同初态、同原始ONNX、同用户目标的成对结果：
- +20mm X：直接路径 timed_out，截止误差14.01mm；适配路径 target_reached，首次报告误差4.49mm。**但18–20秒后段平均目标误差8.29mm、最大9.22mm，不能只报4.49mm。**
- -10mm X（未用于正向20mm标定）：直接路径 timed_out，截止误差11.96mm，后段平均12.67mm；适配路径 target_reached，首次4.45mm，后段平均4.76mm、最大5.28mm。

四组均20秒、未失稳，记录 move-{direct,adapted}-onnx 和 move-minus-x-{direct,adapted}-onnx、adapter_comparison.json。原始量化抖动仍在；正向适配后左/右肘后段逐帧RMS约0.165°/0.129°，不能宣称此适配解决抖动。只有一个初态和两个X目标，不是新场景/全方向泛化。

第一次 adapted 回执存在记录缺陷：motion.reference_delta_world_m 仍保留适配前值；实际参考在独立 reference_adapter.json 和 chain.npz 中正确。已给原目录补 receipt_review.json，保留原证据。随后代码分开 unadapted_reference_delta_world_m 与实际 reference_delta_world_m/ tracker_reference_goal_world_m，反向回合使用修正版本。运行行为与用户目标未受这一记录缺陷影响。

### DEX3 几何：修复 R005 的已知命名失败

原探针引用不存在的 thumb_2_pad_collision。按资产核对改用真实 thumb_2_collision，明确它是胶囊体，不假装拇指有同名pad。移除不需要的 LiveSim/ONNX初始化，使用机器人资产做FK并渲染0/.25/.5/.75/1闭合快照；模型推理0、物理步0。

另修正 right_palm site 的局部坐标被误标成 wrist 坐标的问题：显式由 site_xpos 变换到 wrist 系。实测掌site为[.08,0,0]m。混合拇指胶囊/两指pad几何中心的代理中点随闭合从约[.126,.0423,0]移动至[.1046,.0254,0]m，不能当固定TCP。胶囊对pad最短表面距离由约105mm降至13.5mm，但它不是物体可用开口宽度，也没有形成抓取验证。产物 dex3-geometry-01/geometry.json 与五张快照；已实际查看张开与半闭合图。

### 失败、限制、下一步

- 直接联网读取目录第一次受 sandbox 禁止socket，随后走正式审批的公开只读请求；未改沙箱设置。没有安装包、修改账户或调用repo私有gateway。
- 全量源码并未下载：仅51份相关文本，不能说已完整复现其运行环境/历史实验；公开源本就不带模拟器、权重和原始模型会话。
- 普通 actor 仍未接入；0.5s观测寿命与模型延迟、姿态接口、TCP/contact、原始量化运动质量都是实际未解决项，不能靠Markdown宣称完成。
- 同回合NOTES可迁移，示范视频先用于目标关系/阶段顺序；人类手轨迹直接重放到G1、humanplus检索和跨场景视频ICL均未实现或验证。
- 下一步保留“任务目标/真实状态/tracker参考”三者分立，在连续反馈下改进参考适配并做保持与姿态验收；不继续扫描量化/低通参数，不把局部矩阵逆映射直接设为默认或迁到真机。

R006连续诊断窗口已完成900秒时限，summary=time_limit，无人工动作、无抓取评价；未收到人工通过反馈，不能把这个时限完成记成人工验收。

## R009 — 2026-09-15 — SIMPLE 门任务与 GPT-as-Policy 双路线重构审计

### 当前目标与来源

读取用户指定的两个历史线程：`01a0a061-f6e3-7a53-b0f8-a858f6a84635`（SIMPLE/数据生成规划的外部会话导入）与 `01a0a061-f7e1-75d3-9b79-9bc251c193b4`（EXP8A P0F runtime parity及执行器），并与 APA 的最终 spec、executor、status 和本地 GPT-as-Policy 固定快照交叉核对。目标是说明旧 SIMPLE 门任务，然后定义 Direct GPT-6 与 π0.5/Hybrid 如何共同调用 ScaleBFM。本轮只读审计并写设计说明；模型/API调用0、仿真0、真机0。

### 已确认的旧任务

旧任务注册名是 `simple/G1WholebodyCloseDoorTeleop-v0`，实际为关门而非开门。C0=双手空闲、右手关门；C1=双手持物、右侧骨盆关门；Cneg=持物静止。旧 generator 读取 door pose、hinge、q/dq、contact、role 等特权信息，不能作为视觉 policy。最终 C0 生产没有执行原设计的完整 S0–S6 自适应状态机，而采用固定 oracle：机器人 yaw 约0±5°，双肘约1.2rad/肩pitch约0.2rad，whole-body reference 沿X推进0.6m、5s minimum-jerk并保持5s，通过门板中部碰撞关门。窄门角批中36/36有 door event，33/36 positive，3条因硬关节限位包络失败。

旧判据为 door qpos≤−0.16rad 连续17个50Hz tick，q>0表示开；因此用户现在要求的“开门”必须重建方向与 success predicate，不能仅改 prompt 文案。现有003资产证据只确认铰链和门板 collision，没有确认可动 handle/latch；首版能力应命名 `push_open_door_panel`，抓把手拉门另作后续资产能力。

### 新架构结论

GPT-as-Policy 不提供可直接 import 的通用策略类，可复用的是持续 agent、分层 Markdown、最新 observation/request 绑定、host 边界校验、短 chunk、执行后复观测、同回合 NOTES，以及 Hybrid 中“上一段 outcome / 下一段 intent”分开审查的 gate。

三条可归因实验臂共用同一 execution harness：Direct GPT-6；π0.5-only；GPT-6+π0.5 Hybrid。Direct先检验RGB反馈+harness+ScaleBFM。原仓库π0.5输出ARX X5 14D关节动作，不能送入G1；本地现有的是UMI-4/WB14数据合同、canonicalizer、Wave-0 preflight与未训练头HOLD 3/3，没有humanoid开门checkpoint。π0.5必须在左右腕/踝pose、pelvis SE(2)、hand字段的G1任务空间上微调，再由按名映射和SO(3)重编码的adapter生成ScaleBFM reference；Hybrid另加student/edit/eef gate。π0.5-only必须保留为基线。

统一 harness 只向actor暴露RGB、本体、实测腕pose、reference/error、夹爪命令和同回合回执；door qpos/contact/reward只在隐藏evaluator。策略输出短有界任务空间动作，harness编译成50Hz WB14/VR5 future reference；DEX3由独立手控制器执行。GPT思考期间ScaleBFM 50Hz和PD 250Hz继续运行。当前0.5s观测寿命改为两阶段提交：执行前只做漂移/版本检查，超限返回STALE_PLAN，不静默重锚旧目标。

### 当前阻塞与下一步

当前RSI只有右腕位置接口，没有腕姿态tool；right_palm不是标定TCP；DEX3 closure不是接触/抓力；原始ONNX抖动仍在；单姿态reference adapter不能承担门接触；π0.5没有已训练G1开门权重。实现顺序已写入 `ref/SIMPLE_DOOR_GPT6_PI05_SCALEBFM_DESIGN.md`：先接入003门并复现旧关门oracle作为布线检查，再做左右腕SE(3)/DEX3无门验收，之后定义push-open隐藏evaluator和Direct，最后训练π0.5并做π0.5-only/Hybrid同预算评测。

### 本轮失败记录

首次线程读取使用`turnLimit=100`，接口上限为10而失败；第二次`maxOutputCharsPerItem=30000`，接口上限为20000而失败，均按工具合同修正。外部导入线程把工具日志包成普通消息，关闭includeOutputs仍产生约20万token输出；后续改读最终工作区产物。一次宽泛rg命中大量episode，改为最终spec/runtime/GPT-as-Policy核心文件定向读取。本机已无旧`/home/galbot/lizekai/SIMPLE`目录，只保留APA规格与快照；没有远程重跑、修改旧环境或把本地缺失误报成资产不存在。

## R010 — 2026-09-15 — UMI-4 四点执行合同与项目 skill

### 当前目标与架构修正

用户明确 ScaleBFM 使用四点控制，并要求按 GPT-as-Policy 的模式先在一个任务形成
skill，再以同一 skill 扩展任务。本轮将四点固定为双腕和双踝；公开顺序为腕、腕、
踝、踝，ScaleBFM 14-body active index 为 3、6、10、13，所有边界按名称映射。

这里的 skill 分成三层：Codex `SKILL.md` 保存工具流程、回合记忆与验收规则；任务训练
后的 humanoid π0.5 保存视觉到四点 proposal 的权重；ScaleBFM 只把验证后的四点轨迹
跟踪成 q29。没有把 Markdown 描述成梯度训练，也没有让 GPT 输出 q29 或力矩。

### 已实现

- `rsi/four_point.py`：`FourPointPose`、严格具名 mapping、世界平移、绕世界 pivot 的
  SO(3) 旋转，以及位置 minimum-jerk／四元数最短路插值。
- `rsi/scalebfm.py`：默认且只允许 `UMI-4`；构造后复核实际 active body name。
- `rsi/live.py`：四点观测／reference／误差、完整四点绝对 pose 命令、双 DEX3 closure、
  34 帧未来轨迹和逐点执行回执；保留旧右腕方法作为诊断兼容层。
- `rsi/policy_harness.py`：严格 direct action schema；direct 工具集
  `loco_start/scalebfm_act`；hybrid 工具集 `loco_start/pi05_infer/loco_execute`；最新
  observation path、immutable request、proposal 目录与执行证据落盘。π0.5 未配置时明确
  失败，不生成替代动作。`FourPointBackend` 是未来 SIMPLE 的最小协议。
- `tools/four_point_rollout.py`：无模型调用的 HOLD、右腕 X 平移、右腕 yaw smoke，保存
  头部／右腕 RGB。
- `.cursor/skills/loco-manip-four-point-policy/`：项目 skill、控制合同与训练协议。seed task
  固定为视觉抓取并抬起红块，通过后再扩展放置、双臂和门任务。

README、actor 合同、policy prompt、viewer manifest 与 SIMPLE 门设计已同步 UMI-4 当前
方案。历史 R000–R009 和 artifacts 未改写。

### 测试与真实执行证据

先新增测试得到预期红灯：`artifacts/R010/tests-before.log` 因
`rsi.four_point` 不存在产生三个 import error。实现后逐步运行，最终 27 项 unittest 全部
通过，日志 `tests-tools-after.log`。测试覆盖名称顺序、缺失／多余点、非单位四元数、独立
旋转结果、插值端点、UMI-4 mask、陈旧观测、重复 request、direct/hybrid 工具集合与
未连接 π0.5 的显式失败。这些检查不认证物理跟踪或抓取。

原始 ONNX 做了两次零运动四点 HOLD：

1. `local-hold`，duration 0.5s，最终左／右腕误差 27.05/21.96mm，双踝
   3.18/1.81mm，状态 `timed_out`。
2. `local-hold-rgb`，duration 1.0s，最终左／右腕 29.78/21.11mm，双踝
   3.30/1.85mm，状态 `timed_out`；物理未失稳，进程正常退出不改变该失败判定。

第二次回合的 head RGB 中红块可见但尺度较小；right-wrist RGB 主要被机器人自身遮挡，
不能作为抓取证据。图和 observation JSON 均在
`artifacts/R010/local-hold-rgb/observations/0001/`。两次运行额外 GPT/LLM/API 调用均为0。

### 失败、已知原因与未知解释

- 首次读取 ScaleTrack 对象时漏加 locomanip `PYTHONPATH`，得到
  `ModuleNotFoundError`；按已知解释器合同重跑后确认 UMI-4 active names，未改环境。
- 查找预想的 `direct_context.md` 失败；上游该目录实际只有 `eef_control.md` 和
  `teacher_context.md`。后续以真实 `run.py/schema.py` 与这两份文件为准。
- 三次文档补丁因同路径重复操作或精确空格不匹配被拒。失败补丁没有部分应用；入口文件
  已立即恢复并以小补丁完成。
- HOLD 已确定的现象是脚跟踪好、腕跟踪差，且与此前原始 ONNX 腕部厘米级偏差一致。
  尚不能据此断定是 UMI-4 模式、初始 reference、FSQ 或训练域；需要同状态输入对照。
- 图像问题已分为头相机目标尺度与腕相机自遮挡，不能归因给 tracker。

所有改动保留。它们修复了合同缺失，但没有跨过 seed task 的 tracker/vision gate。

### 下一轮

不调用 GPT，先在相同 qpos 与 reference 上记录 UMI-4 和 VR-5 的 policy_task、mode mask、
离散 code、q29 target 与四点误差；VR-5 只作诊断对照，不回设生产模式。若差异集中在
pelvis mask/anchor，再检查 model_38000 的训练 mode 分布与已有 UMI-4 成功回放初始化；
若 q29 目标相近而腕误差不同，再查参考 pose 与资产负载。并行把头相机提高分辨率，核查
右腕相机 extrinsic/遮挡，而不是用隐藏物体 pose。HOLD 通过后才运行平移、旋转和抓取。

## R011 — 2026-09-15 — 四点局部控制、完整 SE(3) 回执与双 DEX3

### 当前目标与中间层结论

本轮继续执行红块 seed skill 的底层 gate，不调用 GPT/API。GPT/π0.5 仍只输出四点
SE(3) 与夹爪；ScaleBFM 仍输出 q29。新增研究对象是 harness 内的局部腕控制器，
它在 PD 层使用机器人本体误差，不读取方块位姿、接触、奖励或成功真值。ICL memory
负责同回合任务推理，不能替代这个 50/250 Hz 控制层。训练与部署必须固定同一
control profile，否则四点 reference 到实际动作的映射会漂移。

### Jᵀ 位置补偿

复用 `Loco_manip` 的 `HandForceCompensation`，只测试已有回放配置：2000 N/m、
30 N·s/m、20 N 最大笛卡尔力，不加 gravity comp，不扫参。29 关节按名称映射，
每个 4 ms 物理子步重算 `JᵀF`，与 ScaleBFM PD 相加后统一限幅；正式默认保持关闭。

- 10 秒 HOLD：双腕尾段平均位置误差从 41.1/44.4 mm 降到 7.2/12.2 mm；腕 20 ms
  位移 p95 从 0.286/0.185 mm 降到 0.119/0.129 mm，未失稳、未触发臂力矩限幅；
  右腕笛卡尔力 88.9% 子步达到 20 N 上限。
- 右腕从各自新鲜观测锚点 +20 mm world-X：无补偿最终最大四点误差 16.0 mm、
  `timed_out`；Jᵀ 候选为 4.0 mm、`target_reached`，实际右腕终值约 +23.0 mm，
  右腕力饱和 44.2%，没有稳定停止或臂力矩限幅。

证据为 `artifacts/R011/hand-force-paired/summary.json` 与
`hand-force-right-x-paired-02/summary.json`。窗口
`viewer-hand-force-01` 使用同配置、table/cube world-X +0.1 m，15 分钟有界；启动
与逐 tick 记录正常，人工抖动结论尚未收到，不能写为通过。该 Jᵀ 路线在既有
Loco_manip 真机文档中已因高任务空间刚度退役，因此即使当前仿真位置有效也不能
直接迁到真机。

### 修复完整 SE(3) 成功判据并停止旋转分支

发现旧 `target_reached` 只检查位置，姿态命令未实现也可能报成功。先加测试得到
预期红灯，再加入每个 link 的符号不变四元数角误差；现在要求位置 <0.01 m 且姿态
<0.05 rad 同时连续 5 tick。完整测试 30 项通过，日志
`tests-rotation-receipt-before.log` 与 `tests-rotation-receipt-after.log`。

右腕绕自身 pivot 做 +0.08 rad world-Z：无补偿因位置误差 29.9 mm 超时；Jᵀ 候选
位置误差 3.1 mm，但最大姿态误差 0.068 rad，超时。实际相对锚点旋转向量约
`[0.019,0.057,0.045] rad`，不是纯 Z。随后复用真机同源 6D `WristPI` 的唯一默认
配置做第三路对照；位置误差 3.0 mm，但最大姿态误差 0.076 rad，实际增量约
`[-0.008,0.076,0.068] rad`，姿态积分接近 20° 上限，仍超时。原始无补偿实际
增量约 `[-0.014,0.028,0.072] rad`，也有横轴耦合。证据
`wrist-pi-right-yaw-paired-02/summary.json`。没有放宽阈值或继续扫参；旋转接口
保留，训练 gate 未通过，分支暂止。

### 双 DEX3 与失败记录

`gripper-both-open-close` 在 free space 做双手 open→closed→open，8 秒未失稳。
左右闭合目标最大误差约 0.00115/0.00112 rad，重新张开残差约
0.00133/0.00129 rad。它只证明机械手指响应，不证明可夹住方块。

失败均保留：第一次 probe 用系统 Python，因无 MuJoCo 在仿真前退出；动作 probe
第一次猜错 mapping 字段 `position`，在 tick 250、创建移动命令前退出，目录
`hand-force-right-x-paired/failure.json` 已注明；两次定向读取把 GPT-only 文档目录
误当成独立 `run.py/workspace.py`，实际宿主在共享 `skill/run.py`；一次 settings/method
路径同样猜错；一次 `git status` 确认当前目录不是 git 仓库；一次多文件文档补丁因
ROBOT_CONTRACT 上下文不匹配整包拒绝，随后按精确行拆分完成。上述都不是控制器性能失败。

下一步转到 DEX3 nominal grasp frame/TCP 与视觉接近，不死磕旋转。独立 Codex
app-server 尚未接入；现有 `tool_specs` 与进程内 harness 仍不能冒充已注册动态工具。
额外 GPT/LLM/API 调用 0，未上真机、未改受保护环境、未删除数据。

## R012 — 2026-09-15 — task-skill 生命周期、active component 与隐藏抓取验收

### 当前目标与 GPT-as-Policy 迁移边界

本轮把“先做成一个任务 skill，再扩展其他任务”拆成三个不同产物：Codex skill
保存工具合同、决策循环和同回合 memory；任务训练产生单独的 humanoid pi0.5 权重；
成功回合、固定配置和独立评测组成 task bundle。上游 GPT-as-Policy 的 SKILL.md
本身不是在一个任务上训练出来的 checkpoint，不能把 Markdown 与学习权重混称。

新增 `rsi/task_skill.py`，以 DRAFT/CANDIDATE/FROZEN 记录生命周期。当前工程阈值为：
固定合同与 execution-profile SHA、至少3次原生训练成功进入 CANDIDATE；至少5次独立
评测且成功率不低于80%、无 actor 特权输入和未解 gate 才可 FROZEN。它只作确定性
判定，不训练、不自动晋升数据。新增红块 task adapter，当前明确为 DRAFT。

### 隐藏 evaluator 与动态工具 host

新增 `LiftEvaluator`：宿主内部以 reset 时方块高度为基准，抬升至少5cm并连续13个
50Hz tick 才返回 success；稳定停止返回 failure。actor packet 只含
`in_progress/success/failure`，不含方块 pose、高度差、阈值或 dwell。新增
`LocoManipToolHost`，Direct 只允许 loco_start/scalebfm_act，Hybrid 只允许
loco_start/pi05_infer/loco_execute；同一 backend/回合记录，输出必须落在 rollout root
的新目录内。fake backend/pi0.5 的 dispatcher 测试2/2通过，但它还不是已启动的
Codex app-server，也不代表真实 pi0.5 或 SIMPLE 已连接。

### active component 修正

第一次右手开发 oracle 用2.5cm对角 pregrasp 步，在接触前超时。回执最大位置误差
11.8mm、最大姿态误差0.0818rad；原因是完整四点目标没有表达本步只想平移右腕，
未改变的姿态残差也阻止 `target_reached`。因此 waypoint 新增
`active.position/active.orientation` 名称集合：调用仍提交完整四点，host 从当前
reference 出发只覆盖 active 分量；到位门只使用 active 分量，同时回执继续报告
全部四点位置和姿态误差。空集合、重复名、未知名均拒绝。针对测试8/8通过。

### 开发 oracle 结论与停止点

第二次只将步长降至1.5cm并使用 right-wrist position-only mask，其余 proxy、duration、
Jᵀ 参数均不变；仍在首个 pregrasp chunk 超时，active 右腕位置误差21.3mm，方块
位移严格为0。两次运行都标记 `PRIVILEGED_DEVELOPMENT_ORACLE_NOT_POLICY_DATA`，
不能进入 ICL、pi0.5 训练、训练成功计数或视觉评测。按预定规则不做第三次调参；当前
blocker 是 model_38000 + 固定 Jᵀ 候选在该方向上的重复位置控制，不是 TCP 或夹爪。
证据在 `artifacts/R012/oracle-grasp-right-01`、`oracle-grasp-right-02` 与对应日志。

### 测试、窗口与失败记录

task lifecycle/evaluator/harness 针对测试11/11通过，最终全套测试39/39通过；
component-mask 针对测试8/8、tool-host测试2/2通过。此前 Jᵀ 人工窗口完整运行900秒并
以 time_limit 正常退出，未收到本轮用户人工抖动评价，不能写为视觉通过。

失败记录：第一次 thread 读取用 turnLimit=20，接口上限10而被拒；随后限定参数并在
内存解析。两次多文件文档补丁分别因同一路径重复 Update File、训练协议换行不匹配而
整体拒绝，均无部分修改并改为小补丁。两次 oracle 都是算法/能力失败，其他导入、测试
与补丁错误不是机器人性能失败。模型/API调用0；未上真机、未安装依赖、未修改
`psi_deploy`/`.venv-psi`、未删除数据。

下一步不继续 Jᵀ/WristPI/步长 sweep。先保持 core skill 和 tool host，单独更换或修复
可重复的腕部执行层；其通过 position/rotation primitive 后再恢复机械 oracle。SIMPLE
backend 和 task-trained humanoid pi0.5 provider 仍是独立未接依赖。

## R013 — 2026-09-15 — 动态几何工具、Hybrid gate 与 Codex app-server transport

### 当前目标与保留设计

本轮目标是把四点 skill 从进程内 dispatcher 接成可运行的 GPT-as-Policy harness，
而不调用模型。Direct 工具集现为 `loco_start`、`four_point_translate`、
`four_point_rotate`、`scalebfm_act`。两个 geometry 工具只从最新 robot observation
编译完整四点 target 和 active mask，不执行 backend。backend 在 launcher 构造 host
时固定；GPT 无权在 MuJoCo、未来 SIMPLE 或真机之间切换。

审查旧 Hybrid 实现发现一个实质错误：`loco_execute(proposal_path)` 会盲执行 π0.5
proposal，文档所说的 GPT gate 实际不存在。现改为
`loco_execute(proposal_path,response,output_dir)`；response 是 GPT 审阅后的完整 UMI-4
chunk，可原样采纳或有界替换 proposal，并再次走 Direct 的同一 validator。proposal
绑定生成它的最新 observation，只能消费一次；格式校验失败不执行，物理调用开始后
不能重放。这保留了上游 GPT-as-Policy 的关键 teacher/student 分工，没有复制其集群、
benchmark 和网络恢复代码。

新增 `CodexPolicyAdapter`，按本机 codex-cli 0.154 schema 构造 initialize、thread/start、
turn/start，核对 thread/turn ID，把 `item/tool/call` 路由到同一 `LocoManipToolHost`，并
把结果按 `inputText/inputImage` 回包。malformed JSON 只产生已审计的
`no_execution/retryable` 失败；未知运行异常仍为 fatal。新增独立 stdio JSON-RPC
transport 与 `tools/codex_direct_sim.py` 显式入口。模块导入、单测和 initialize 都不会
创建 model turn；只有用户运行 direct 入口才使用 Astra 套餐额度。

### 验证、失败与当前结论

新增测试先按预期失败：geometry tool 未注册、app-server/stdio 模块不存在、Hybrid
schema 缺 response、malformed JSON 直接抛出。实现后全套46/46通过，证据为
`artifacts/R013-tests-full.log`。真实 app-server 第一次握手因 sandbox 禁止在
`~/.codex` 初始化 SQLite 而 stdout 关闭，日志保存在
`artifacts/R013/app-server-handshake`；允许该本地状态写入后，第二次只执行
`initialize → initialized → close` 并成功，证据在
`artifacts/R013/app-server-handshake-approved`。另一次上游 settings 只读检查猜错
文件路径，以及一次用系统 Python 测试缺 SciPy，均已停止并改用已有项目解释器；
它们不是控制器或模型失败。一次包含本段说明的多文件 patch 因 README 目标句跨行而
整体拒绝，随后按文件拆分完成，没有部分修改。一次现状 `rg` 的双引号 pattern 含
Markdown 反引号，shell 误将其中的工具名作命令执行；没有写操作，随后改用单引号
pattern 重跑且无陈旧现状命中。

当前结论仍是 DRAFT。app-server transport 可用，但没有 `thread/start`、`turn/start`
或模型调用；真实 humanoid π0.5、SIMPLE backend 仍未连接。机械 blocker 没变：
model_38000 + 当前 Jᵀ 候选在所需方向的右腕位置重复性、腕部旋转、DEX3 TCP/closure
标定和视觉闭环抓取尚未通过。因此本轮没有启动自主抓取，没有新增训练成功或评测计数，
LLM/API 调用0。下一轮应更换或修复腕部执行层，先过确定性 primitive，再运行一次
Direct Astra seed episode；π0.5 训练只使用该固定 execution profile 下的合格数据。

## R014 — 2026-09-15 — active-aware WristPI、夹爪阶段、π0.5 gate 与 SIMPLE bridge

### 当前目标与 execution profile

本轮目标是修复四点 reference 到 ScaleBFM q29 之间的腕部执行层，并补齐能够训练和复用
task skill 的外部接口；没有调用 GPT、π0.5 或其他模型。采用 Loco_manip 真机同源的 6D
`WristPI`，但只将它用于当前 MuJoCo execution profile。旧 Jᵀ 控制器因高任务空间刚度不再
作为部署候选。ScaleBFM 仍使用 model_38000 UMI-4，关节顺序仍以接口文档规定的串行 q29
为真值，跨 SIMPLE 边界只按关节名映射。

### 抖动根因与 active component 修复

初次把 WristPI 接入时，左右腕未声明 active 的位置和姿态残差仍被积分并施加到 PD 层，
造成双臂同时抖动。`wrist-pi-direction-01` 三次均超时，最大误差 12.43 mm，inactive 姿态
积分达到上限。修复后，inactive 腕的目标在每个 tracker tick 取当前实测 pose，并分别清零
其位置或姿态积分；只对 waypoint 声明的 active component 施加 WristPI。

修复后的固定右腕 +20 mm world-X 三次均为 `target_reached`，最大 active 误差 7.33 mm，
无稳定停止，证据为 `artifacts/R014/wrist-pi-direction-active-mask-01/summary.json`。固定
+0.08 rad world-Z 三次均到位，最大位置误差 9.50 mm、最大姿态误差 0.03746 rad，证据为
`wrist-pi-right-yaw-active-mask-01/summary.json`。这两组是确定性方向测试，不是随机鲁棒性。

旧的完整 pose-hold 仍三次超时，最大误差 11.92 mm；它同时激活无关残差，不纳入当前
合同。为尝试把当前下倾手掌转到更适合水平侧夹的姿态，又做了唯一一次 -0.08 rad
world-Y 测试；三次在 180 tick 后仍为 `executing`，位置误差 6.88 mm、姿态误差
0.053478 rad，高于 0.05 rad gate，证据为 `wrist-pi-right-world-y-negative-01`。该方向
明确失败，不放宽阈值、不继续扫参；一般姿态跟踪 gate 仍未通过。

### 抓取几何、夹爪阶段与机械 oracle

DEX3 资产审计确认 `right_palm` site 位于腕坐标 `[0.08, 0, 0]`，但它还不是经接触验证的
抓取 TCP。已有几何采样显示 closure 从 0 到 1 时三指表面间距明显变化；当前方块边长为
5 cm，不能继续把旧猜测 `[0.125, 0.05, 0]` 当作真值。成熟回放脚本对 6 cm 方块使用了
特定 proximal/distal override，且实际运行从 pick frame 就开始闭合；旧注释所说的
press gate 已被代码删除，不能照抄注释。

先写失败测试后实现纯夹爪 waypoint：允许 position/orientation active 列表同时为空，
在给定 duration 内线性插值闭合量，并把当前命令值和最终 goal 都写进 observation。
终态 `gripper_duration_elapsed` 只证明命令区间结束，不证明接触或抓取。取消动作会冻结
当前闭合值。它消除了为了闭手而伪造腕部 active motion 的合同错误。

采用修复后的 WristPI 运行一次特权开发 oracle。四个小 pregrasp chunk 到位，第五个
超时，整个过程方块位移为零且没有接触；证据在
`artifacts/R014/oracle-grasp-wrist-pi-01`。它表明位置执行比 R012 前进，但宽松 1 cm
到位 gate 会使每段实际位移小于请求，尚不足以到达旧 proxy。该回合标记为
`PRIVILEGED_DEVELOPMENT_ORACLE_NOT_POLICY_DATA`，不进入 ICL、π0.5 训练或评测。

### π0.5 与 SIMPLE 接口审计

Hybrid 现在在创建 episode 前强制校验 π0.5 capability manifest：provider 必须声明
`task_trained_humanoid_pi05`、对应 task skill、`rgb_plus_named_robot_state` observation、
`umi4_se3_plus_bimanual_gripper` action、包含 `head_rgb` 的具名视觉输入，以及 checkpoint
和 normalizer SHA256。现有 M3 `serve.py` 明确把所有图像设为 `None`，输出是 6×130 的
WB14 相对目标并带 mode/active mask，不是四点视觉 response，因此被拒绝作为视觉学生；
没有调用它，也没有用不相关 checkpoint 代替。

SIMPLE 安装中的 `SonicLocoManipEnv` 为 50 Hz 外层、200 Hz physics，原生
`Pi05DecoupledWbcAgent` 使用自己的 joint/WBC 动作链，不等于 ScaleBFM UMI-4。新增
`SimpleActionBridge` 只做具名编译：q29 policy order 到 SIMPLE body order、双 DEX3
目标到左右手 order，拒绝名称集合不一致和非有限值。静态加载真实 SIMPLE `ActionCmd`
成功，q29 顺序相等、左右手名称集合一致、输出 shape 为 29/7/7，证据为
`artifacts/R014/simple-named-bridge-static-01/result.json`。

首次动态 reset 触发隐式资产下载，立即终止并记录
`simple-scalebfm-audit-01/result.json`；随后强制 Hugging Face/Transformers offline 重跑，
确认缺少 `assets_articulated.zip` 中的 `assets/articulated/003/output_mjcf/003.xml`，证据为
`simple-scalebfm-audit-offline-01/result.json`。因此只有静态 bridge 兼容，动态 SIMPLE
backend 仍被本地 asset 003 阻塞；没有下载大文件、没有 model inference 或 physics step。

### 失败分类、保留结论与下一步

控制失败包括：修复前 inactive 积分导致双臂抖动、完整 pose-hold 超时、world-Y 旋转
未过 gate，以及 oracle 在接触前第五段超时。环境/工具失败包括：一次误用系统 Python
缺 SciPy，随后恢复到既有 locomanip 环境；sandbox 内 tmux 因权限失败，按已授权方式在
sandbox 外启动；一次宽泛文件搜索产生 broken-pipe 噪声；一次补丁误改 hand-force tick
计数后立即恢复；三次大文档 patch 因上下文/Unicode 不匹配整体拒绝且无部分应用；
`git status` 再次确认当前目录不是 git repo；R014 状态哈希脚本第一次沿用旧清单中的
`assets/scene_mjx_track_dex3.xml` 相对路径而停止，随后从 `rsi.scalebfm.SCENE` 核实真实
绝对路径并重算。这些不计为机器人性能结果。

本轮保留 active-aware WristPI、纯夹爪平滑 waypoint、π0.5 capability gate、SIMPLE 具名
bridge 和所有失败证据。task skill 仍为 `DRAFT`，训练成功0、独立评测0、模型/API调用0。
下一轮不再死磕 world-Y 参数；先用公开资产几何和可见 RGB 标定一个明确的掌心/指间抓取
frame 与方块宽度闭合量，再做一次无物体特权输入的短程视觉接近—闭合—抬升试验。若该
几何仍要求未通过的手腕姿态，应更换可达抓取方向或执行层，而不是给 GPT 隐藏目标 pose。

## R015 — 2026-09-15 — RGB grounding、显式 EEF 点与可达域停止结论

### 当前目标与新增 harness

本轮目标是把 GPT 看见的目标像素转换成 ScaleBFM 可执行的四点短程动作，仍不调用模型。
先将已有 `wrist_pose_for_local_point()` 暴露为动态工具
`four_point_place_local_point`：调用者必须给出左右腕之一、显式 link-local offset 和世界
目标点；工具保持当前腕姿态、返回完整四点 target、所需 wrist delta 和
`within_single_step_limit`，只编译不执行。它刻意不叫 `move_tcp()`，因为 DEX3 grasp TCP
尚未标定。

又新增 `image_pixel_to_world_plane`：从最新 observation 的具名 RGB calibration 中读取
图像尺寸、fovy、camera-to-world pose 和 MuJoCo `-Z` forward 光学约定，将显式像素射线与
调用者声明的水平工作面相交。`MujocoImageCapture` 现在把这些字段与同一 sim exposure
写入每张图。工具不检测物体、不读取 depth/segmentation/object state，也不执行物理；
未来真机 image provider 需输出同一 calibration contract。Direct 与 Hybrid 均暴露这两个
几何工具，π0.5 proposal/审阅/执行边界不变。

先写测试得到预期红灯：局部点工具未注册/dispatcher 不识别；随后像素函数不存在、视觉
工具未注册。实现后中心射线、偏置射线、平行射线拒绝、工具集合、latest observation
路由、远目标提示和“geometry 不触发 backend”均通过。正式 Direct launcher 另补 250 个
50 Hz tick 的 5 秒 settling，稳定检查通过后才暴露第一帧；settling 不调用 GPT。

### 纯视觉几何取证

第一次数学探针用 RGB 红区中心与 `.656 m` 高度，后验 XY 误差为 7.31 mm；复核发现该
高度包含方块中心/半高信息，因此主动撤销其“纯视觉”资格。第二次只使用 head RGB、相机
标定和 `.630 m` 支撑面：红区中心投影后验 XY 误差 20.22 mm，红区底边中点为 22.96 mm。
这些隐藏真值只在 estimate 冻结后作 developer evaluation，未反馈动作。

真实 stateful episode `artifacts/R015/vision-geometry-chain-01` 在 5 秒 settling 后，从
head RGB 红区像素 `[379.81,348.61]` 投影到工作面
`[0.3405,-0.2373,0.6300] m`，再用显式 `right_palm=[0.08,0,0]` 编译其上方 10 cm 的
pregrasp 点。所需腕 delta 为 `[0.1996,-0.0128,0.0477] m`，工具正确报告不能单步执行；
没有动作、隐藏物体读取或 GPT/API 调用。该结果只证明 RGB grounding 与 EEF 编译链。

### 连续 reach、双脚平移与近桌场景失败

新增 `tools/vision_reach_probe.py`，每段只读取最新 head RGB、相机/工作面 calibration 和
具名机器人状态。默认场景的 vector 方案第一段到位误差 9.29 mm，第二段停在14.24 mm；
改为最大误差单轴后第一段纯 +X 到 9.17 mm，第二段仍停在16.35 mm。两者均在右腕
world-X 约 0.12 m 附近停止，分别保存在 `vision-reach-01` 与
`vision-reach-largest-axis-01`。因此不是对角耦合，停止腕步长/时长 sweep。

随后测试四点整体 +20 mm world-X。双腕误差仅3.70/2.54 mm，但双踝误差仍为
19.98/20.58 mm并超时；静态同时平移双脚目标不能替代交替 lift/plant 步态，证据为
`all-four-x-01`。该路线停止，不让 GPT 用“滑动双脚”扩大可达域。

为把抓取 seed 与 gait 分开，做了唯一一个 table/cube world-X −0.14 m 场景检查。它能
稳定站立且 RGB 可见，但桌面进入手臂当前工作区：视觉最大轴首次 +Z 2.5 cm 在21.43 mm
超时；直接 `.35` 闭合只得到 `gripper_duration_elapsed/in_progress`，随后 +Z 2 cm 抬腕
在13.89 mm超时，fresh RGB 未显示方块被抬起；将 pregrasp 改为支撑面上方3 cm后，唯一
+X 2.5 cm 接近又在25.87 mm超时，未继续闭手。证据依次为
`reachable-scene-offset-01`、`vision-reach-offset-01`、
`vision-triggered-close-lift-01` 和 `vision-step-close-lift-01`。该 offset 场景被拒绝，
不再扫描桌子位置或 closure。

### 失败分类与下一步

能力失败是连续 wrist-only reach、静态双脚平移、近桌场景 X/Z 跟踪和视觉闭合—抬升。
工具失败包括：视觉 dispatcher 测试最初把 calibration 放进 FakeBackend observation，
但 harness 按真实语义用 capture provider 覆盖为 `images=[]`；修正 fixture 后通过。随后一次
fixture patch 因上下文过宽先落到普通 Direct 测试，立即精确恢复并只注入视觉用例。
一次 SKILL/CONTROL_CONTRACT 组合 patch 因段落上下文不匹配整体拒绝，无部分应用，随后
按文件拆分完成。最终全量 unittest 52/52 通过，日志为
`artifacts/R015-tests-full.log`。上述工具错误不计为机器人性能。

保留两项通用能力：同帧 calibrated RGB grounding 与显式 link-local EEF 编译。task skill
仍为 `DRAFT`，训练成功0、独立评测0、GPT/API调用0。当前 blocker 已从“缺少视觉世界点”
收敛为“缺少可持续的全身可达构型/成功示范”。下一轮不再从桌子位置和腕控制参数搜索；
应选一条已有成功的 4 点抓取示范，或先构造无初始接触且目标位于已验证单步可达包络内的
全身初始姿态，再固定该示范形成第一个 task bundle。需要扩大可达域时，必须提供交替脚抬起、
前移、落地的时序示范或 task-trained policy，不能用双脚静态平移冒充步态。

## R016 — 2026-09-15 — 本地成功示范与 5点 motion pool 审计

### 当前目标与找到的成熟管线

继续只读查找可复用的成功示范。本地 `Loco_manip/locomanip` 已有完整
wholebody_grasp 管线：ScaleTrack/BFM 追踪、从 rollout 生成 LeRobot 数据、VLA 评测和真机
部署。其 schema 与当前方向高度一致：head RGB、right-wrist RGB、双腕/双踝4点9D、右手
closure 和 pelvis SE(2)。`source_init.py` 会从同一 `rollout_*.npz` pool 检测 pick frame、
重建四点 motion 并对齐初始全身姿态；这正是当前手调桌子位置所缺的“示范分布内初始化”。

### 为什么现有本地文件不能直接作为成功 skill

全 `/home/galbot/lizekai` 文件名搜索确认没有任何 `rollout_*.npz`，也没有
`grasp_priors.json`。`data/agent` 的15个 outcome 和 `logs` 的98个 outcome 均为
`task_success=None`；没有一条可验证的 autonomous/assisted success 标注。

仓库包含173个 `*_poses_5pt.parquet`，每个都有 head、双手、双踝 wxyz pose 和
0/1 gripper；loader 可直接映射到 UMI-4。源码和数据审计同时确认：这些是30 Hz VR 人体
采集，经零阶保持到50 Hz；全部 clip 都有 gripper latch，但没有物体状态或任务成功标签。
更关键的是 `track_runner.py` 的 region 演示在 gripper frame 直接把物体相对腕部刚性锁定，
其日志里的 `PICK SUCCESS` 是 synthetic attachment，不是 DEX3 物理夹持。按“闭合后右手
上升”排序只能筛 motion shape，不能证明抓取；候选局部窗口仍含显著脚/手位移。

### 保留结论与下一步

这173条 5点 motion 可像 HumanPlus-1000/单段人类视频一样提供 phase boundary、交替脚步和
手部 approach/lift 先验，但必须先按脚点重锚、过滤 support-foot slide、转为当前 wxyz
四点合同，再通过 model_38000 物理 replay 和 hidden native evaluator。它们不能计入
task training success，也不能教出 DEX3 接触细节。

形成第一个 GPT-as-Policy task skill 仍需要一条真实成功 source：优先恢复成熟管线实际使用
的 `rollout_*.npz` pool；若该 pool 不可获得，则从选定 VR/HumanPlus clip 构造四点示范，
但必须重新采集真实 MuJoCo 物理接触成功的 RGB/机器人状态/动作回合。该数据缺口与 R015
视觉 harness 无关。本轮只读，无仿真动作、无代码改动、GPT/API调用0。

## R017 — 无示教 Direct 首次真实执行；接触约束取证（2026-09-15）

**当前目标**：按用户纠正，先测 GPT-6 Astra Direct，无示范、无 π0.5、无跨回合任务答案。
R016 的成功 source 前置条件不适用于此基线。现有环境不修改，新文件统一在 RSI；
全局约束已追加到 `/home/galbot/.codex/AGENTS.md`，原文备份在 `ref/`。

**实施与验证**：沿用 UMI-4/model_38000/active-aware WristPI，不调增益；补充实际
25 fps 视频、每 tick 机器人 trace、真实调用计数、单 waypoint/动作预算/连续超时终止。
策略仅接收 head/right-wrist RGB 和具名机器人状态，第三视角只用于录像。工具计算限制
比上游 full-agent 窄，未声称完全复现其所有能力。

**真实回合**：`artifacts/R017/direct-01/`，Astra/xhigh、ChatGPT 登录、1 个 Codex 回合、
6 次工具调用、4 个物理动作。内部模型请求次数不可见；独立 API 调用0。结果未完成：
位置残差9.38/21.70/29.41/15.45 mm，后三步超时；没有闭合或抓起。模型确实从前进
改成抬高，又缩短步幅，证明回合反馈被使用，但不证明技能成功。墙钟182.25秒、物理
运动14.78秒。6个工具间响应等待中位25.01秒，范围14.68–46.79秒，不具备实时性。

**为什么失败的证据**：`replay-01` 无模型精确回放，四步残差差值0。host-only
接触记录显示 reset 后右手食指已经与桌面接触，后续持续，峰值12.719 N。50 Hz
采样中双臂无力矩饱和，左臂PI附加力矩接近零。不能据此声称所有抖动已解决。

**反事实及其失败**：保持原机器人状态，只将桌沿前移50 mm，原前两目标都通过
位置门限（5.58/9.68 mm）；第三目标因反馈状态变化而超过30 mm限制，被校验拒绝。
仅部分回放，排除训练/ICL/评测。更严格的 `table-clearance-reset-audit.json` 显示
在位移后的场景重新稳定仍有食指接触，否定该候选；没有启动第二个模型回合。
新参数默认0，方块位置未变，旧数据未覆盖。取证脚本已补充失败时保存部分回执。

**保留结论**：初始接触与桌沿约束显著影响本段跟踪，尚非唯一根因；超时不等于
几何不可达。必须区分“临时干预”与“完整reset”。上游MD提供工作流程和同回合记忆，
并非训练GPT权重；无示教Direct仍允许本回合经验。一次试运行不是泛化成功率。

**下一目标**：验证无初始干涉、可见预抓取净空的完整场景，再冻结场景与工具进行
新Direct。之后才做短反馈窗口消融和开发集memory；视觉π0.5、真RTC、Isaac动态后端
仍未接入。已发现 SIMPLE 内 Isaac Sim4.5，不改它的环境，不冒充已在Isaac测评。
详见 `ref/R017_DIRECT_PILOT_REVIEW.md` 和 `ref/DIRECT_RTC_MEMORY_DESIGN_20260915.md`。

## R018 — 持续自我修改 skill 的 Direct campaign（运行中）

**当前目标**：用户授权从自主尝试中跨回合获取经验，以 Astra/xhigh 完成十次独立物理抓取后进入 SIMPLE。恢复 GPT-as-Policy full-agent 的普通计算、图像、笔记工具；不再沿用 R017 的三个超时终止与外部成功示范前置条件。

**已做**：主 skill 初版 679 words /5097 characters，低于上游最大 831/6250；`experience_read`、带轨迹来源的 `skill_update`、版本归档、十次独立 success 计数与视频记录已实现。接触＋抬升＋保持由隐藏 evaluator 验证，closure 不算成功。61 项初始测试通过；追加无推理期限修复后 adapter 六项通过。

**运行证据**：`artifacts/R018/campaign/episode-0001` 仍在实际探索；曾闭合／抬手但未观察到可靠方块共动，策略撤销了抓取判断，随后从腕 RGB 判断方块已掉到桌下并尝试重新定位。目前无已完成成功，不宣称技能已经学会。

**新纠正**：SIMPLE 既有管线在 ds4090，不应因本机某 checkout 缺资产而重复准备；已核实远端目录、环境与 replay/render CLI。早先重复下载已结束，保留产物，不再下载。推理事件旧有900秒上限已修复为完整等待，但当前运行进程尚未热更新。物理暂停与实时推进的区别已明确询问。细节见 `ref/SIMPLE_REUSE_AND_INFERENCE_WAIT_20260915.md`。

**后续**：等待当前回合自然结束，核实 Astra 提交的第一份 skill 修订及其真实轨迹证据，再继续后续独立尝试；不要把进程仍运行当作任务完成，也不要把旧 SIMPLE／oracle 成功混入当前计数。

### 第一回合完成后的回执

episode-0001 自然结束且 Astra 完成修订：47 个物理动作、57 次动态工具调用，墙钟1539.64秒、仿真120.16秒；步数预算结束，没有运行错误，没有原生抓取成功。15次到位超时不能等同15次模型失败。腕 RGB 0024/0025 支持短暂方块共动，0026 明确分离；稳定抓取未成立。

模型自己形成 v1 skill（819 words /5989 characters，sha256 `b30a99e12c7ae859806033e900c2704a11a1e9cb1d0e3b11f51ee7170d580861`），记录提前调姿、分阶段闭合、短抬后独立保持的待验方案及16条真实证据路径。episode-0002 已自动启动，其 SKILL.md 与 v1 按字节完全一致，证明跨回合经验被载入。目前成功0/10。第1回合视频与 `evaluation.json` 均位于 `artifacts/R018/campaign/episode-0001/`。追加推理等待回归后全套62测试通过。

### 原样回放与 prompt 纠正

第1回合47动作原样回放，全部末端位置残差差值0，6008次 ScaleBFM 推理、GPT调用0、无场景修改。最高抬升52.0mm，但满足50mm＋多指接触的最长连续段只有7tick（0.14秒），未达25tick保持条件。不是模型从未夹起过，也不能事后放宽判据计成功。证据 `artifacts/R018/replay-episode1/contact_summary.json`，仅供host诊断。

旧任务文案未明确5cm/0.5s完成条件，是本次prompt不足。第2回合中通过 app-server `turn/steer` 补充了明确目标，ack返回原turn，不重启回合，不传递回放物体真值。源TASK也已同步修正供以后启动。另：初始头相机 nominal scene 投影与红色像素bbox差<1px；腕相机初始无目标可见，不能强行做双视角匹配。标定检查在 `artifacts/R018/host-camera-calibration-audit.json`，不提供给actor。

### 第二回合完成与第三回合继续

episode-0002：51动作、55次动态工具调用、墙钟1927.52秒、仿真120.42秒，预算结束且没有运行错误；成功0/10。Astra自行生成v2 skill（819 words /5957 characters，sha256 `f7d1d02b972ae857b22084992d060c30d17c4948ca2c6d0f7ec896b8ec405a99`）。v2已明确5cm/0.5s、允许保持夹持的小幅转动、整手越过方块顶部的净空。episode-0003启动快照与v2 SHA完全一致。

第二回合51动作原样回放全部残差差值0，无GPT调用。最高抬升27.2mm。short-hold阶段前12tick还有三指接触，随后丢失，101tick中88tick有桌面接触；**实际滑脱发生在主动释放前**。因此模型的“仅凭转动而释放不合理”是应修正的判断规则，不能据此推出这次夹持实际上稳定。最终更强闭合及释放后掉到地面。证据 `artifacts/R018/replay-episode2/contact_summary.json`；不传给actor。

运行工具审计还发现：每次相对`cat SKILL.md`失败，以及使用系统Python导致PIL/SciPy导入失败；不是文件写权限拒绝。已给当前episode-0003/agent补齐起始skill快照与workspace解释，通过正式turn/steer明确使用原有locomanip_sim解释器，ack仍为原turn。没有安装包，没有发送在线动作目标。请求留存 `artifacts/R018/runtime-clarification-steer-request.json`。

落盘tool_result缺少LearningHost后补状态字段的问题已先复现再修复；新代码全套63测试通过（`artifacts/R018/tests-receipts.log`）。源码也补齐以后启动时的agent/SKILL.md。以上源码修改尚未热加载到持续运行的旧进程；历史回执不回填、不覆盖。当前回合的任务／工具说明通过steer生效，二者不可混淆。

### 第三回合：首次完整物理抓取成功

episode-0003完整归档：native_success、26动作、30次动态工具调用、墙钟1000.74秒、仿真55.46秒，运行错误null。计数为3次尝试中的1次成功（1/10），不是稳定成功率或跨场景泛化。

原样回放26动作全部位置残差差值0；实际最大抬升65.1mm、末帧62.9mm，最长连续满足50mm＋多指夹持条件162tick（3.24秒）。末帧仍有拇指／食指／中指接触，没有桌面接触。回放GPT调用0、不计新增成功。独立取证 `artifacts/R018/replay-episode3/contact_summary.json`；原视频 `artifacts/R018/campaign/episode-0003/video/episode.mp4`。

Astra自行形成v3 skill（828 words /6139 characters /5254非空白字符，均在上限内）。保留0.45闭合、短抬与保持后继续有界抬升的成功经验，声明单次成功不证明重置可靠性，并纳入正确Python解释器。episode-0004已自动开始，继续视觉重定位和反馈执行，没有播放原样回放。模型经验中的“终末serialization失败”在host RPC审计中未复现：最后scalebfm_act为success=true、无host error；保持为模型侧工具呈现的待核说法，不据此修改物理结果。

### R018 episode-0004：第二次原生达标，但终帧已掉落

- 42 个物理动作；103.90 s 仿真／1297.27 s 墙钟；Astra xhigh 完整复盘后提交 skill v4，831 words／6030 chars。episode-0005 的 starting skill 与 v4 字节一致，SHA256 d9dbd3621e9b1eb6e63ee3f5597374803a4a9b54ed4f4cbec849e58983762a6e。
- 模型从双目终帧自行发现物块回到桌面，明确区分原生达标与终帧保持。这次不能报告为“结束时仍握住”。
- host-only 零 GPT 精确回放的42个动作误差差值全部为0：最高抬升67.220 mm，连续满足50 mm＋至少两类同手手指受力接触的最长时间3.26 s；105.84 s首次达标，108.60 s最后仍满足，108.90 s终帧方块回到桌面且无手指接触。
- 判定：满足预先定义的50 mm／0.5 s抓取目标，计入原生达标；终帧保持为false。保持这两个字段独立，不回改阈值、不把回放另计成功。
- 原因边界：最后一个有界动作在 evaluator 锁存成功后继续运行到自身结束，随后发生滑落。模型已自行在v4记录成功回执与终帧保持的区别。精确接触／物体状态仅用于host审查，没有注入在线actor。
- 复盘再次提到“terminal serialization failed”，但原始 app-server 最后动作记录 status=completed、success=true，返回文本含 rollout_finished=true／native_success，host result.error=null。尚无证据证明宿主序列化失败，不按模型措辞虚构故障。
- 证据：artifacts/R018/replay-episode4/contact_summary.json、campaign/episode-0004/evaluation.json、video/episode.mp4。当前2次原生达标／4个独立回合，episode-0005运行中；尚未进入SIMPLE物理。

### R018 提示输入精简与 SIMPLE 验收准备（磁盘变更，当前进程未热更新）

- 检查episode-0005的16次动作回执，累计给actor传入252,217字符文本，平均15,764字符。command_status和execution重复包含完整锚点、请求目标、批准目标及内部fingerprint。
- adapter只在发送给模型的文本副本中去掉这四类重复字段及下划线内部字段，保留状态、误差、实际观测和full_receipt_path。原始result文件不变，仍能读取完整命令差异。
- 先写回归测试复现未精简失败，再修复；64项检查通过。一个真实回执样本由15,738字符降为9,813字符（37.6%）。这不是延迟或token费用的实测降幅，不能混称。当前loco-learn-0915仍使用启动时旧版本；留待安全启动的下一阶段使用。
- 为SIMPLE准备DoorPushEvaluator：场景须从关闭状态开始且正方向为推开；有手部子树和门子树的有效受力接触，角度相对起点增加至少30°、连续1s仿真时间、无站立保护失败才成功。角度和接触只留在host，actor仍只看三态结果。重复update而不推进仿真时间不会累计；被动门运动、失稳、回合内重新关合的情况有测试。
- 尚未用该新判定启动SIMPLE物理。该步骤没有修改当前抓取的物理参数、判定或skill。

### R018 SIMPLE 后端接入准备

- LiveSim 新增可接收已有 MjModel／MjData 的入口，保留已有base pose、关节状态和仿真时钟；默认仍是原桌面场景。抽取原物理循环为 `_advance_physics`，用于SIMPLE覆盖，默认数值计算不变。
- 改前保存100控制tick的qpos／qvel／ctrl，再用改后代码运行同一段：逐元素完全一致、最大差0，记录于artifacts/R018/simple-adapter-preparation/control_extraction_parity.json。该校验无GPT调用、不计任务成功；69项回归检查通过。
- 新增SimpleLiveSim：四点→同一model_38000→按名字映射的target_q→原SIMPLE decoupled_wbc；WristPI增量以tau/kp转成等效q增量，由原SIMPLE PD和限幅执行。身体／手指名称来自实际SIMPLE joint index，未按位置猜测。
- SIMPLE入口要求每次原生env.step恰好推进20ms；已有桌面的0.25m总位移诊断边界参数化，SIMPLE独立实例可用2m，单步3cm／0.1rad限制不变。这个较大边界是场景许可范围，并不证明已学会走路。
- 未启动SIMPLE场景、尚未通过真实SIMPLE站立或推门验证；仅接口测试通过。当前运行中的抓取进程仍使用原先载入的实现。

### R018 episode-0005：第三次原生达标，终帧失去夹持

- 第二次抓取修正了两类手指的接触高度，最终有独立2s保持动作；原生success、动作target_reached。第六个独立回合已继续运行。
- 43动作精确回放全部误差差值0；即使加载控制函数抽取后的代码，仍完整重现当前进程轨迹。最高抬升52.975 mm，连续满足既定条件2.14 s；终帧仅抬升12.974 mm、无手指接触、未接触桌面。不能把该终帧描述为稳握。
- 当前预先声明的50 mm／0.5 s历史达标累计3次（episode3/4/5）；已核验的结束时仍握住只有episode3。两项分列，保留原结果、不回改阈值、不用回放充数。
- 这也暴露当前同步harness的限制：evaluator成功锁存后，有界动作仍继续到结束，所以最终图像可能晚于达标时刻。十次预定义标准的学习门槛与真机所需长期持物稳定性不是同一结论。后续持续物理／RTC评测必须另外报告保持时间与掉落。
- 证据：artifacts/R018/replay-episode5/contact_summary.json、campaign/episode-0005/evaluation.json。

### R018 episode-0006 的记录标准澄清

- 发现episode3-5复盘反复沿用“terminal serialization failed”，但原始服务完成记录success=true，host result.error=null。该措辞可能指模型侧编排错误，不能当作已证实的执行器故障传播。
- 已向第六回合的原活动turn发送一次正式turn/steer，要求记录错误原文和所属层、区分未执行的解析失败与已完成物理动作，并在下一版skill中限定未证实的故障说法。没有提供物体真值、接触数据或动作目标，没有重发动作／重启turn。
- 请求：artifacts/R018/evidence-clarification-steer-request.json；app-server确认仍为turn 01a0a656-9182-7f63-90b3-39ea82c6f0e4。当前正式累计3个原生达标／5回合，第六回合继续运行。

### R018 episode-0006：第四次原生达标，第七回合继续

- 28个物理动作；原生success、最后动作timed_out。本回合28个动作的回放误差差值全部为0，完整执行后继续记录到动作结束。
- 最高抬升63.887 mm，连续满足既定夹持条件1.24 s；终帧方块回到桌面，无手指接触。继续分列历史达标与终帧保持。
- Astra 已按澄清修正未证实的终态序列化归因，并完成v6自我修订。第七回合初始skill与v6字节一致，SHA256 5625cd2265e66f56c302ecf7ed98df2ac7271a85ea8344e8bcbb09b6dc25858a。
- 正式累计4次原生达标／6个已结束独立回合；精确回放确认4次，终帧持续符合条件1次。未启动SIMPLE物理。
- 新增tools/audit_grasp_campaign.py，每次仅增量读取尚未汇总的回放记录，输出host-only audit_summary.json和retention_audit.json；从原连续接触tick计算终点连续保持时间，回放永远不增加独立任务次数。

### R018 对照诊断：参考姿态漂移与闭合量

- 对episode3-6最后一次.45闭合后的五个动作核查：20/20次参考四元数都等于上一次实际测得的腕姿态。相对抓取时腕姿态，终点变化分别为.156/.129/.114/.184 rad。仍保持住的episode3变化大于已滑脱的episode4/5，因此现有数据不能把漂移认定为唯一原因。证据：artifacts/R018/attitude_audit.json。
- 独立、零GPT的单变量回放对照：episode6原记录中6个.45右手闭合请求替换为.50，其余期望航点、场景和控制器保留。28个动作全部执行，error=null；原生结果in_progress，最高抬升43.077 mm，无达到50mm持续夹持，终帧回桌。
- 原.45轨迹最高抬升63.887 mm、连续达标1.24s。对照不是“握得更紧就解决”；仅支持这条轨迹中.50没有改善，不能推广为所有姿态都应选.45。停止对同一参数继续盲扫。
- 对照由闭环到位状态产生了40ms累计执行时间差，动作残差最大变化1.210mm；这不是要求数值一致的原轨迹回放。所有源文件保留，录像明确标注COUNTERFACTUAL，未加入主campaign计数，也未把接触真值或该轨迹提供给当前actor。
- 产物：artifacts/R018/counterfactual-episode6-grip050/replay_result.json、retention_audit.json、video/episode.mp4。新增闭合量替换参数先做非法值失败测试，修复后通过；实际对照也完成。
- 在线episode7独立选择了“保存.45闭合后的抓取时四元数，试抬时固定该四元数”的新尝试。结果尚待验证。

### R018 episode-0007：第五次原生达标，固定抓取姿态仍未解决终帧夹持

- 本回合从自身经验出发，在试抬与保持中固定抓取时四元数；早期保持姿态误差约.011-.019rad，动作到位。但第一次抓取未可靠持物，随后重新抓取。
- 共35物理动作；最终native_success，最后一段timed_out。精确回放误差差值全部0：最高抬升58.336mm、连续达标0.54s，终帧回到桌面、无手指接触。姿态跟踪改善不能直接推出接触稳定性改善。
- 完整自我复盘后提交v7，第八回合已经启动，初始skill与v7字节一致。正式累计5次原生达标／7个已结束独立回合；终帧持续符合条件仍1次。未进入SIMPLE物理。
- 产物：artifacts/R018/campaign/episode-0007/evaluation.json、replay-episode7/retention_audit.json、audit_summary.json。对照回放不计入这一计数。

## R018：额度错误重试缺陷与验收范围扩展

第8次物理尝试在21动作／53.0模拟秒后收到usageLimitExceeded，未能完成经验修订。第9至431号记录均为0动作额度错误；它们不是423次物理抓取失败。旧主循环对所有错误sleep30秒后重试，累计424条额度错误。当前账户恢复后第432号已正常执行，仍使用v7 skill。保留所有记录，未重置券、未降级、未调用另计费API。

先写usage错误与慢推理区分测试，初始ImportError复现缺少保护，再加入usage_exhausted检测和quota_pause回执，4个skill-learning测试通过。旧进程不能热更新，因此独立quota-guard只在新增额度错误的result落盘、且主进程没有模型子进程时终止循环，不打断当前推理。

用户确认新的总验收：10次抓取之后进入SIMPLE，推门至少10次成功，其余所有可用操作任务各至少1次成功。已静态保存91个本机环境注册入口；包括不同机器人、变体和缺件，注册数不等于可运行任务数。逐项记录兼容与阻塞，不把其他机器人直接映射至G1。

### R018，第8次中断轨迹审计与抓取优先

21个原动作精确回放，所有残差差值为0；方块一直在台面、最大抬升0。该回合因套餐额度中断，不能归因为物理抓取方法已证伪。第432号是恢复额度后的第9次真实物理尝试；423个零动作编号不作物理尝试。用户再次强调先10次抓取并初步优化skill，当前暂停SIMPLE额外准备，未启动SIMPLE任务物理。

已准备的跨任务接口测试覆盖task目标、真实起始时钟、无方块平面/胶囊假设；录像按关节名恢复free root与门铰链测试通过。SIMPLE draft skill为640words/4538chars/3848非空白，尚未经任务验证，未替换抓取canonical skill。

### R018，物理第9次／目录episode-0432：第6次原生成功、第2次终态保留

39动作；前一抓取在抬升时图像确认滑落，随后重新张手定位、下降，发现闭合几何接近桌面，调整间隙与接触后以0.40闭合重新抓取。实际最大升高53.969mm，终态53.639mm，连续有效双指抓持0.56s，终态thumb/middle接触且无台面接触。全部39个回放残差差值为0。只能声称满足既定0.5s条件，尚非长时稳定证明；闭合量与姿态/接触位置同时变化，不能判定0.40是普适最优。

Astra完成v8修订，SHA 2701cb93274b7a76fa620ada1509d54a95dca67388414800046b49f43ec97170；{'words': 804, 'characters': 6208, 'non_whitespace': 5345}。接续episode-0433确实使用v8快照。原运行进程未热更新，相对SKILL.md仍需由root补齐；不重启进行中的模型回合。当前完整软件测试74项通过，不替代物理验证。

### R018，记忆按需读取与序列化分层审计

episode-0432最后scalebfm_act的app-server事件为completed/success=true，15548字符文字结果已返回；没有host序列化错误。Astra自报functions结果边界出现failed to serialize JavaScript value，此客户端层报错无法从当前host事件独立核实，不能说成物理执行失败。回执已单独保存serialization_audit.json。

experience_read原样返回4条完整长lesson/大量路径，v8时默认56751字符。先用17000字符lesson测试复现，然后实现1600字符预览、3个证据路径及按version完整读取；默认15767字符，完整原记录逐字保持不变。7项相关测试通过。该修改尚未进入旧后台进程，不为热更新中断推理。

### R018，物理第10次／episode-0433：第7次原生达标，终态滑落

35动作；首次0.40包围滑落后重新定位、改变接触几何，第二次最大抬升58.095mm、连续双指有效抓持0.82s；最后命令姿态误差0.112671rad/位置0.729mm，终态回桌无手指接触。35动作全部精确回放残差差值0。原生达标7次，终态保持仍2次。Astra完成v9，SHA 3cac35e8032b4991edf92b3a5c21fc852f61024e332834099d8b6fb271e52b5c，{'words': 781, 'characters': 6190, 'non_whitespace': 5349}。

末段对比ep3/432/433：记录采样的右臂关节离硬限位均超过1rad，总输出力矩未接近上限；局部腕PI可达1.5Nm限幅，但成功与滑落案例都出现，不能定为独立原因。当前不改控制增益、不向actor提供隐藏对象/接触诊断。

快照与额度保护监控已单独升级，仅替换监控进程，未打断模型。新回合自动补齐与immutable SKILL快照相同的agent/SKILL.md。

### R018，episode-0434：主skill篇幅澄清（不含动作指导）

当前v9为781words/6190chars/5349非空白，连续多轮在长度上限附近花费时间压缩细节。通过正式turn/steer只补充：上限不是目标，约500–650words若足够更佳；保留目标、接口、限制和可迁移实证步骤，详细角点/逐帧坐标/长错误转录保留在原轨迹与证据，lesson简明。未改变物理目标、动作或成功门槛，未提供隐藏状态。请求ID rsi-skill-compact-clarification-20260915-ep434；app-server确认原turnId，推理未中断。源代码中也补充同样的未来启动提示。

### R018，物理第11次／episode-0434：预算内未达标，v10精简

47动作、121.16模拟秒。三次主要包围/抬升均经公开视觉确认回桌，尝试过0.40/0.45/0.50闭合及有界姿态修正，均未证明可靠保持。回放47动作残差差值全部0；最大抬升35.222mm，终态抬升10.315mm仍接触台面，不符合5cm要求。不能把该回合说成模型推理失败；是接触/抬升目标在物理预算内未完成。

Astra完成v10，SHA b8b836265d0fc645dcb053f63011a19fd8f0b7526a7ead387537380ad973d9ae；{'words': 649, 'characters': 5105, 'non_whitespace': 4434}。当前原生达标7/10，终态保留2次；下一回合episode-0435使用同版快照。SIMPLE未启动。

### R018，保留早期自身成功经验的检索

发现默认只返回最近4条经验，持续失败后会遗忘早期已成功的程序。先用“较早一次成功＋近期连续未完成”的测试复现：原来返回versions[3,4,5,6]，应保留自身首次成功version2。改为“近期记录＋最早native_success”共至多4条，默认仍为短预览，具体版本可取全文；6项memory测试通过。这是检索基线，不宣称首次成功最优。源代码改动不冒充已热更新。

当前episode-0435通过正式turn/steer澄清可以选择性读取同一campaign memory/experience.jsonl、版本化skill及其引用的原public rollout。未注入隐藏接触/物体数据或人类示范；旧坐标不能直接重放。请求rsi-memory-retrieval-clarification-20260915-ep435得到当前turnId确认。未来workspace也明确列出可读的自身经验归档。

### R018，物理第12次／episode-0435：第8次达标、第3次终态握持

31动作、86.20模拟秒。最大抬升52.394mm，终态50.317mm；最后连续有效抓持1.92s，终态thumb/index/middle接触、无桌面接触，闭合0.45。31动作精确回放残差差值均0。末动作因姿态0.062778rad超时，位置误差1.005mm；不能把姿态跟踪超时当作抓持失败。该回合无单独的追加终点hold，1.92s是原命令执行尾段真实物理证据。

复盘出现数分钟无事件的reasoning等待；核实控制器/模型进程存活后完整等待，自行恢复输出，没有取消或重发。随后Astra完成v11，SHA 7d0b36b209c379e68914f98c8e7ab3d45740039d77a0fcd59ed6c065d0d0a139；{'words': 713, 'characters': 5562, 'non_whitespace': 4827}。episode-0436使用同版快照。当前8/10原生达标、3次终态握持；SIMPLE尚未启动。

### R018，纠正过强的自有skill复用限制

核对v11发现两处绝对限制：never ... replay coordinates、never replay historical poses。这可能把防止盲放误解成禁止验证后复用自己的成功策略，与用户“先学成skill、再基于skill继续任务”的目标不符。独立物理重置不要求每次从零规划。

通过正式turn/steer澄清：允许检索自己此前成功的程序、候选waypoint/相对参数；先与本次公开RGB及机器人状态比较，必要时适配；每个动作仍用新obs ID/command ID和真实注册服务，并看新观测验证，条件不符即恢复。不引入人类示范、对象真值、外部成功轨迹；host诊断回放仍不计新策略成功。要求下一次Astra自己的skill_update把绝对禁令改为reuse-and-verify。请求rsi-skill-reuse-clarification-20260915-ep436已由当前turn确认，没有取消推理。后续启动源提示亦同步澄清。

这是prompt/harness约束修正，尚不能声称已提升成功率；继续用后续独立物理结果验证。

### R018，物理第13次／episode-0436：未达标、验证后复用写入v12

43动作、120.30模拟秒；原动作回放全部残差差值0。最大抬升34.802mm，连续合格抓持0.00s，终态抬升-629.892mm。多次包围与增加闭合未保持，反复接触让方块靠近桌沿，最后失去支撑。模型基于公开视觉复盘；主机诊断仅用于独立验收，不反馈对象真值。

Astra完成v12，SHA 8fb41e6a13aaa4e62c4f9650eb0435206a5922bd05acbf20ed8746e2ef7597d9，size={'words': 783, 'characters': 6050, 'non_whitespace': 5245}；明确允许检索自身成功程序并用本次RGB/机器人状态验证、适配后执行，替换旧的绝对历史坐标禁令。episode-0437确实使用新快照。计数仍8/10原生达标、3次终态握持，SIMPLE未开始。该prompt修正的实际收益待后续验证。

### R018，物理第14次／episode-0437：第9次达标、第4次终态握持

模型主动检索435的自身成功public rollout，将当次观测与候选姿态/相对参数比较后逐步执行；25动作、70.64模拟秒，最终原生成功。重放全部残差差值0；最高54.190mm，终态50.262mm，连续有效双指抓持2.40s且持续至终点，thumb/middle接触、无台面接触，闭合0.45。末动作位置1.556mm、姿态0.076100rad，姿态跟踪超时不等于物理抓取失败。

Astra完整复盘后更新v13，SHA 9474369849b844895dc14e6b3b4693e846cbefd73b945f7cde05c3e241a58aed，size={'words': 737, 'characters': 5795, 'non_whitespace': 5036}；episode-0438已使用该快照。原生达标9/10、终态保持4次。此次复用成功是单例支持，尚非成功率或泛化提升结论。未启动SIMPLE。

### R018，物理第15次／episode-0438：第10次达标，抓取阶段门槛完成

25动作、72.60模拟秒；原动作回放全部残差差值0。最大抬升57.148mm，终态55.070mm，连续有效双指抓持2.54s持续至终点，thumb/middle接触、无台面接触、闭合0.45。model保持gpt-6-astra/xhigh，完整等到turn结束，没有额外计费API。

Astra更新v14，SHA b0333112a55fec64b1617b0547c1b1f0edfe4f3b2f96c02aa9fa9e086b463ae0，size={'words': 748, 'characters': 5951, 'non_whitespace': 5181}。正式台账10/10原生成功，其中5次终态保持；15次真实物理尝试包括1次额度中断，423个零动作额度记录不算物理尝试。每个有效回合都有视频与复盘，诊断回放不额外计数。这是固定重置场景的自身经验学习，非zero-shot或held-out泛化/实时真机验证。至此允许进入SIMPLE；入口HOLD推理审计不计推门成功。

### R019，SIMPLE入口传感器差异修复

抓取10/10及v14完成后启动入口，原适配器报No gyro sensor found，0次模型推理/0次env.step。查明g1_sonic只有挂在torso_link的imu_gyro，不能改名冒充pelvis。新增RSI内存场景构造钩子，在pelvis上创建独立gyro_pelvis；原环境/资产/包均未写入。腰部转动反例测试先失败、实现后通过，确认pelvis和torso角速度可区分。

修复入口artifacts/R019/entry-pelvis-gyro/result.json通过：29关节命名一致、四点存在、双目640x360、一笔model_38000输出有限、模型SHA一致。只是reset/HOLD推理，不计任务成功。下一步native PD与50Hz实际步进/站立诊断，仍不使用模型套餐调用。

### R019，真实控制与推开侧场景

stand-native-01：350次native env.step＝7.00s，50Hz tracker/200Hz native PD，未启用弹力带，无失稳，门角维持-0.1745329rad。双目可见门。原关闭门场景的正向开门靠近机器人，故建立明确标注的push-open变体：门资产绕关闭门板质心旋转180度，保留关闭门板中心及机器人站位，正向门运动改为远离机器人；不向actor暴露几何诊断。

非零门角测试发现mj_setConst(model,data)会重置当前qpos，首个stand-push-side-01已标INVALID_SETUP.json并永久保留，不算任务。错误：未在检查测试结果后再启动依赖诊断。改用独立scratch MjData重算常量，测试确认门角、质心和时间保持。stand-push-side-02重新通过350步7秒诊断，初末门角均-0.1745329，opening_dot从-0.48337变为+0.48337。

SIMPLE bootstrap skill由抓取v14适配，原版本不变；task改推开30度/1秒，移除方块平面与胶囊假设，50/200Hz，240秒物理预算，允许指定旧public经验检索。长度813words/6146chars/5311非空白；transfer-manifest保存来源和SHA。先有测试再增加task-specific budget，3个LearningHost测试通过。模型仍astra/xhigh，等待完整turn。推门0/10，尚未有策略尝试结果。

### R019，原生PD不是ScaleBFM训练PD：独立对照

当前首轮推门使用native profile，多次厘米级位置残差，尚无门接触。并行独立实例做25mm无接触微扰，未改正在推理/执行的回合。native→checkpoint残差：左腕X58.337→8.768mm、左腕Z63.632→1.720mm、右腕X44.054→2.964mm；各组固定相同随机种子、实际关节目标按名称映射，视频/配置/实际位移完整保留。左踝Z目标25mm，两组实际高度变化约0，残差均约25mm。

结论：当前桥接选用SIMPLE/Sonic默认PD造成明显手部跟踪劣化，下一回合应使用ScaleBFM对应增益。不能推论所有控制问题已修复；单脚卸载/步态问题独立存在，尚无推门成功。产物tracking-profiles-01及tracking-profile-comparison.json，全部0 GPT调用、不计任务成功。

### R019，任务范围与MuJoCo/Isaac资产解耦

静态91入口中19为native Sonic；疑似缺失的4任务实际在g1_wholebody_teleop_efficiency_tasks.py集中注册，19均有定义。首次离线reset/HOLD接口检查13通过、6因HSSD USD目录缺失失败。源代码确认MuJoCo只消费HssdSuite原config几何，load却顺便检查USD并向/tmp复制贴图。RSI内存中仅对MuJoCo使用同一配置构造HssdSuite，未伪造目录、未换场景参数；元数据等价测试通过后6项复查均通过。19任务现在是“接口可用”，成功计数均0，不等于完成物理任务。其余G1旧控制器变体及非G1入口仍需兼容性处理，未从总清单删除。

4090已存在scene0和水龙头scene8完整USD（后者866MB），不复制整包、不下载。Isaac首次无回执因关闭应用遮蔽异常，已先保存错误再关闭；第二次明确缺vMaterials_2。第三次仅对该缺失MDL使用原生默认桌面材质，保留其他资产材质和全部几何/门角，结果待查。源配置不修改，差异写进渲染回执。

### R019，Isaac渲染通过；大幅度单脚诊断仍不抬脚

4090 isaac-smoke-03成功输出5帧，编码退出0；已取回首帧并目视检查门、手、桌面均可见。录像为episode_isaac.mp4，回执明确physics_rollout=false、new_task_successes=0；只替换缺失的桌面MDL，不能当成Isaac物理任务成功。

四点单步默认3cm不变；新增按链接声明的限幅，仅独立诊断实例把被测踝提升到8cm，手腕仍3cm。反例测试先失败后通过，默认脚部拒绝6cm、诊断脚部允许6cm、手腕仍拒绝6cm。foot-response-01对checkpoint PD左右踝各测试6/8cm，4例均超时而未失稳，实际Z变化绝对值均小于0.018mm。排除“仅因3cm请求太小”的假设；不要继续盲目扩大命令，需检查输入敏感性和支撑协调。0 GPT调用、0任务成功；未改第一轮正在运行的Astra或控制参数。

### R019，输入敏感性、其他任务接口与失败退出

input-response-01固定同一真实站立状态及两组历史，只改变参考，不执行目标。左踝Z+8cm引起左腿关节目标L2变化0.16037rad，右腿0.09248rad；右踝也有非零响应。排除目标完全丢失/模式屏蔽，动态不能抬脚的原因仍未闭合；不据此断言模型无法行走。

通用native任务桥仅在host保存env.step返回的terminated/reward，丢弃原生obs/info，不再额外调用奖励函数。初始即成功的场景拒绝计数。水龙头源标准是abs(articulate_joint_0)>0.7rad并积累奖励；SIMPLE原生每step内部调用compute_reward两次，此口径保留并单独注明，不能改称1秒保持。34项相关测试通过；水龙头原布局7秒站立检查通过、未自动达标，物体初态和外力保留。首轮Astra/xhigh已启动，独立memory和skill，bootstrap768words/5868chars/5078非空白。未共享隐含物体信息。

推门第一轮62动作、240.04模拟秒，物理预算结束；12003条host记录门角变化0度、手门接触0次，未成功，完整模型复盘仍等待中。后段反复保持到耗尽预算暴露harness缺陷：缺少策略主动结束失败尝试的接口。新增finish_attempt：至少3个已完成动作、无在执行动作、当前public证据、失败原因与下一假设才可结束，不推进物理、不计成功，随后仍必须skill_update。先复现缺失接口再实现，4项LearningHost测试通过。正在运行的旧进程不热更新、不截断推理；新接口仅后续回合生效。

### R019，推门两次完整复盘与Isaac录像

episode-0001最终完整turn结束，wall2497.93s，skill v1为808words/6133chars/5302非空白。Astra自己审计发现手腕上漂约0.60/0.55m、脚无前进，区分姿态到位与抓取/接触，并记录一次skill_update引用agent RPC目录被拒的提交错误，改用public rollout后成功提交。该错误不算物理故障。

episode-0002使用checkpoint PD和v1，4动作/10.28模拟秒/wall403.45s；三种接近候选无脚部推进，最后恢复支撑成功，策略主动finish_attempt并完整复盘，无推理截断。手腕短时跟踪约2.6mm，不能替代脚步前进。v2为828words/6195chars/5342非空白，SHA699d6c66f961543e6d5e7b6b21bdea99ea5d23e2ee8bc97a9789354aff832ec0。下一假设由Astra提出：先受限横向支撑转移，再尝试不同摆脚。第三轮使用该v2继续，0/10推门。

首轮241帧Isaac重渲染完成并取回，保留原模拟时长，artifacts/R019/isaac-door-0001/episode_isaac.mp4；仅缺失桌面Iron_Sheet.mdl走默认材质，物体/门/机器人状态按原命名关节恢复。明确不是Isaac物理试验，不新增成功。后续新回合host trace补充归一化动作、原始/补偿后关节目标、腕PI力矩和实际最后子步力矩，manifest保存关节名称与runtime源码SHA；均不供actor读取。静态提取19项原生任务成功定义到native-task-criteria.json，两项继承定义仍需追溯父类，未把未完成任务移除清单。

### R019，第三轮与摩擦假设排除

episode-0003共3动作/7.28模拟秒/wall424.41s，踝滚转和双踝偏航未建立支撑转移，恢复支撑后主动结束，完整复盘形成v3（SHA0255a702b5c4ea0e9254da5f1d233fc2bdd252617142f61dfdf1e726db4880ed）。下一假设由Astra提出：在保留足部支撑时尝试双腕横向移动，检查髋/腰及相机运动，仍未验证。

SIMPLE body joint摩擦0.2Nm与旧抓取资产零摩擦不同；单因素置零摩擦的四组6/8cm抬脚仍全部超时、Z变化绝对值小于0.020mm，无失稳。故不将正式场景摩擦改零。旧抓取资产在相同5ms步长下的第一个6cm左脚诊断也未抬升（Z约0.0019mm），支持问题并非SIMPLE独有；只完成这一例，不夸大到全部机器人对照。该诊断在收尾调用不存在的LiveSim.close时报错，结果序列化中断，已保留infrastructure_error.json及完整视频/trace并修复收尾；不算策略尝试，不丢弃该错误。

### R019，用户新增要求：共享抓取经验、任务skill与详细说明

重新对照GPT-as-Policy的robodojo-gpt-only-rollout/SKILL.md及teacher_context.md：其分离短skill、任务上下文、EEF接口、持久notes/history，并强调公开决策摘要而非私有思维链。该仓库本身不证明“一个共享skill”与“每任务一个skill”谁更优；本项目的跨回合skill学习与主动结束失败尝试是明确的本地拓展。

新增共享核心skills/loco-manip-core/SKILL.md，提炼真实抓取v14/437/438的检索-验证-执行-纠错过程，未导入固定目标坐标、旧碰撞胶囊、闭合值或人工动作示范。任务专属经验仍由Astra修改并版本化。推门把共享核心和原v3的Tested experience原文组装成636words/5027chars/4376非空白；pre-hybrid-SKILL.md与hybrid-assembly.json保存原文及前后SHA。这次host组装不是新策略成功，也不是Astra伪署名的修订。

任务说明ref/tasks/simple-push-door.json和simple-open-faucet.json在新回合workspace.json中完整提供：目标、初态语义、操作对象、阶段指导、可观察的进展/失败条件、完成标准、控制限制及禁止替代的目标。它们给出任务知识和定性指导，不给物体位姿/接触真值或成功轨迹。主skill的合成长度仍单独受原全部上限约束。

experience_select记录选择的来源ID/路径/SHA、理由、当前场景适配及未复用内容，保存到public skill_selection.jsonl；新SIMPLE回合第一次动作之前必须记录选择。skill_update增加change_summary、task_specific/shared_candidate和已选来源；共享候选只入本任务shared_candidates，不自动覆盖核心。旧版本/完整公开轨迹/回执/错误及经验journal保留。14项相关测试通过，两个skill通过官方格式校验。第四轮推门使用这个结构和详细说明启动，旧水龙头回合完整运行，不热改。

后续比较计划：暂以共享核心+任务专属修订作为待验证默认；共享单skill易传播任务特例，完全独立skill易重复探索，均不是已证实结论。先离线统计现有选择/反复失败/动作与推理成本；控制接口可用、出现SIMPLE成功后，再冻结相同初始经验、控制器、任务说明、重置条件和预算，对单共享/独立任务/混合结构做小样本对照。学习期允许改skill，冻结测评不更新。不能把不同PD、不同任务说明和不同随机初态下的差异宣称为skill结构因果效果。

### R019，共享结构验证、苹果迁移与脚部全程审计

全套87 tests及12 subtests通过。推门第四轮已在首次动作前记录来源选择（shared_core/task_current_skill/task_experience），并在失效模式变化后再次选择；7动作/17.24模拟秒后主动停止，完整模型复盘仍等待。侧移曾产生28.745mm相机位移，但踝位移仍<0.378mm；配合双腕位置跟踪也不能抬脚，不能将侧倾写成行走。

复查既有foot-response、去摩擦反事实及旧抓取资产共9条完整轨迹，不新增物理/模型调用：被测脚全程最大增高0.00985–0.09275mm，排除仅终点统计漏掉真实离地。证据foot-trajectory-audit.json。下一独立单因素诊断只将左踝8cm参考时长2s改为0.5s，限幅/正式task接口不改；待结果决定是否需要连续chunk，不预设其有效。

新增simple-pick-place-apple.json：详细任务、原生验收与语义目标分离、抓取/搬运/释放指导；不包含物体坐标或人工成功动作。7秒站立预检通过，无弹力带/无初始成功；RGB中碗和目标形状可见，但MuJoCo缺原始材质，明确保留此视觉限制。苹果任务使用共享核心和独立memory开始首轮astra/xhigh，与推门/水龙头并行；没有task成功结果。原生苹果判据只是苹果接触碗且脱离手并积累奖励，不能把它直接称为稳定置于碗内。

推门第四轮完整turn结束：7动作、17.24模拟秒、wall624.73秒，0成功，v4已保存选择来源/变更摘要/范围字段。第五轮仅采用Astra自己提出的姿态约束协调候选，未改控制器。

单因素时间诊断：左踝8cm参考由2s改0.5s，峰值增高0.19787mm（2s为0.08451mm），仍超时且无离地。不能凭此否定未测的连续协调轨迹。旧指定会话external-import-turn-24/25复用到的教训是D1真实滚动本体历史与D2真实未来帧；当前ScaleTrackInferFn._infer_common采用移位后追加，LiveSim.tick构造不同未来插值，未发现旧缺陷同态重现。旧oracle分数与部署33步时标不移植为本项目结论，model_38000接口及训练5..32步约束仍是当前依据。

### R019，第二20x账号接入与继续执行交接

用户明确提供并授权codex-account-2/run.sh。未改启动器、未读密钥。实际app-server只读路由检查返回ordinaryUsageAllowed=true、planType=pro、通用周期13%已用，没有创建验证模型回合。学习run_episode已固定经该launcher启动，无裸codex/API回退，新增model_backend.json及结果路由字段。相关13项测试通过。当前桌面及已运行旧回合仍主账号，不能声称热切成功。

推门第五轮完整结束：5动作/13.08秒/wall515.89s、无成功，v5为760words/5883chars/5109非空白。双腕姿态约束仍不能建立步进；改实际姿态基线的到位不能当成原参考恢复。水龙头首轮完整结束：74动作/240.20秒/wall3238.53s，无成功，v1为793/6132/5314；引用agent RPC文件被拒后自行纠正。next_call已补真实可引用证据，非法路径报错点名；反例先失败后修复，16项相关测试通过。

原生SIMPLE手部碰撞是mesh而非旧抓取胶囊。新增robot-only末节mesh腕系包围范围与链接原点；测试世界旋转平移不变性及输出仅含机器人，原生水龙头模型检查通过，0模型调用/0物理动作。范围明确不是接触面/TCP，不含物体信息。通用SIMPLE新回合启用，旧回合不热改。

水龙头第二轮已启动（simple-faucet-02-0915），新进程路由第二账号，采用混合skill、详细spec和机器人几何。苹果首轮主账号进程继续完整执行。按用户要求，第二账号CLI supervisor在rsi-account2-supervisor-0915中接续后续监控、审查、编码和仿真迭代，固定astra/xhigh，workspace-write+auto review，不关闭sandbox。交接ref/ACCOUNT2_CONTINUE_20260915.md列明目标、进程、计数、经验、限制和下一步，JSONL日志artifacts/R019/account2-supervisor-0915.jsonl。此项是继续执行，不是目标完成。

### R019，第二账号接管：苹果首轮完成与水龙头初始化重试缺陷

苹果episode-0001完整turn/skill_update结束：15动作、44.20模拟秒、wall799.21秒，未成功、主动停滞。v1 SHA aba5230d9f3d3d76ff9e7b1a008440ed0b304c82b0b17598b0d859ebc99c420b，733words/5753chars。公开证据显示手未进入视野、腕姿态跟踪受限；退后再升高恢复高度，不能定为绝对工作空间不可达。下一候选为更早建立可见接近、平移与姿态修正分离，并使用已准备的原生手指几何。

推门episode-0005也完整结束：5动作/13.08秒，v5 SHA 9fc4cd0c5bf4737281a0a0fdd59160a10c8757dc4c026e18063b82b8cab8e9b6；双腕位姿约束未建立迈步，采用实际左腕姿态后到位不等于恢复原参考。五次完整失败、0/10。下一步优先审查连续参考接口，不无限微调腕部参数。

水龙头episode-0002通过第二账号run.sh连接，initialize回执CODEX_HOME为codex-account-2/home，thread/start确认gpt-6-astra/xhigh。但loco_start反复报repeated name apple_mesh_convex0；0物理动作、0仿真秒，不算第二次物理失败。旧adapter把后端ValueError当可重试参数错误，外循环在每个完整turn后再次提示启动，共22turn/45动态工具调用。为不截断模型，在turn_022写盘边界设置一次性目录guard；完整turn/completed后才触发退出。guard已归档到completion_boundary_guard，并从RPC恢复真实turn_022.json；原result.error保留，详见infrastructure_review.json。未伪造skill_update：本次无物理开始，旧host不允许修订，原task skill保持。

RSI修复：SIMPLE场景装配前仅为重复ObjectActor标识拷贝asset实例并唯一命名，优先保留target/container名称，资产几何、位姿、采样seed和动力学不改；不修改外部环境/资产缓存。后端构造异常与actor参数错误分开，返回不可重试/未开始/回合结束，允许基于初始化错误提交基础设施复盘，再完整等待turn结束。21项相关测试通过（首次测试命名空间与fixture frontmatter错误已修正）。原失败seed=2站立诊断已启动，尚不能宣称真实任务路由执行或物理成功。

### R019，第二账号真实物理执行、失败复盘与连续参考诊断

水龙头原失败seed=2在名称修复后通过7秒/350步站立（无初始成功）；episode-0003显式仍用seed=2。与苹果episode-0002一起，model_backend、initialize的第二账号CODEX_HOME、thread/start的astra/xhigh和首个真实动作全部核实，account_route_verified.json已保存。账号路由现在有实际任务执行证据；episode-0002的零动作初始化记录仍不算物理尝试。

水龙头episode-0003完整结束：14动作/26.92模拟秒/wall521.95秒，12到位、2超时，主动停滞，未成功。腕位置准确未确认活动件或转动；下插出现108.33/83.52mm脚部漂移，撤回后稳定但不作因果断言。v2 SHA d9925bd4df77af9e1855d8548765a22bfff747cf8e585c151b46d731ad703a2a，741words/5809chars；新候选为斜视辨认小控制件、先空中验证姿态再接触。完整原因、证据、排除项和下一改动保存于failure_review.json；共2次水龙头物理失败、1条零动作基础设施失败。

新增ReferenceSequence和独立合成参考诊断，不修改在线actor单路点接口。3项插值测试通过，包括未来采样跨段、四元数单位长度及单段与原插值逐元素一致。continuous-reference-01未显式控制Python/NumPy随机源，四例作为个体诊断保留，配对因果比较标记PAIRING_INVALID；初次FK审计因此遇到关节集合不一致，错误日志和infrastructure_error.json保留。

补齐create_closed_door_backend的原生随机源控制后，continuous-reference-02协调两例初始qpos/qvel哈希完全一致。左踝最高增高：逐点等待0.08551mm、连续0.06087mm，均未离地；脚部单独两例为0.08911/0.02708mm，初始命名qpos最大差9.63e-29、combined哈希不同，不声称逐位一致。只能排除这两条具体连续候选的有效性，不能否定所有连续行走参考。

control-chain-audit-02对实际原生29关节命名PD检查：静态+0.01rad目标产生的命名力矩与预期完全一致、未推进物理。既有协调参考抬脚阶段，网络关节目标在固定实测base的FK下把踝置于实测值下方约0.3–2.7mm；这不是稳定性证明，但不支持“网络已输出明显抬脚、只是名称映射丢失”的解释。下一独立诊断验证更完整交替步进参考是否能产生离地，幅度/起始姿态同时改变，明示为可行性探针而非单因素比较；不向actor提供合成轨迹、不计任务成绩。

### R019，苹果第二轮、命名验收修复与新操作任务

苹果episode-0002完整结束：19动作/75.64模拟秒/wall853.71秒、未成功，v2 SHA7d54b1fb01d4579ef2c84256119af5097f8b1f74f990ff50122e7ad4e85000b7，725words/5739chars。没有握持动作；侧移在腕姿态误差仅.0014rad时仍几乎不前进，因此不能全部归因姿态跟踪。v2提出低位先整形腕yaw/roll以改善拇指外侧净空，再测对角接近。failure_review.json保存原因/证据/排除项/下一改动；episode-0003按v2继续。水龙头episode-0004按v2继续。

发现部分原生接触reward以名称子串判断目标，第一版apple__distractor标识仍会匹配apple。RSI命名修复改用不含任何原标签的rsi_aux标识，保留原asset对象、目标名称与几何；新增检查确保目标名不在重复实例名内，10项相关测试通过。先前水龙头使用阀角验收、苹果没有distractor，不受此潜在接触误计影响；没有因此回改历史成绩。

更完整的合成交替步进UMI-4诊断：左/右踝最高增高.126/.226mm，腕前移约9cm，仍无可靠步进；在同检查点已有VR-5模式添加骨盆支撑转移的可行性探针得到左踝2.85mm增高/18.55mm前移，右脚基本未动。幅度/参考/模式同时变化，不作单因素结论、不认定离地、不升级正式controller。接着用机器人自身几何IK生成可达全身参考、对UMI-4/VR-5/Full-14模式做独立验证，保留完整接触与位姿证据；此合成参考不提供给actor，也不算任务尝试。

新任务simple/G1WholebodyBendPickTeleop-v0：本地源确认target为cracker box，native reward=clip(delta_z/.10,0,1)、成功阈值.8，即相对初始升高8cm，无握持接触/保持时间要求。详细spec强调形状识别、原生白材质、整手净空、检索抓取v14并适配和物体-手共运动；不提供目标坐标。seed1站立350步/7秒通过，无初始成功、无弹力带；已启动独立bendpick-campaign首轮，仍第二账号astra/xhigh，不把预检记为成绩。

### R019，全任务静态兼容性与几何可达参考诊断

保留91注册入口，task-compatibility-02/report.json逐项记录：19 native Sonic桥已预检；63其他G1的29命名关节拓扑存在，但旧LocoManipulationEnv/控制器没有当前decoupled_wbc 20ms桥，不能等同任务不可用；2个G1InspireWholebody本地MJCF缺失；6非G1机器人缺少model_38000要求的关节；1个VegaFindNGrasp gym入口对应task未由原生import注册。未删入口或把预检算成功。报告通过MRO追溯全部已有compute_reward/check方法，补齐XMovePickSimToReal和苹果继承验收定义。首个审计未处理缺注册KeyError，已保存错误并修复成逐条记录。

kinematic-reference-01只在几何检查阶段发现约12mm残差，未执行候选，不能算物理策略失败。第二版让IK在受限8cm范围内调整机器人自身骨盆高度，以免侧移时支撑腿过伸；最大加权残差8.53e-7后才执行。三种模式用同一full-body参考SHA2718d0ba5b3b1c3e9032776d3b1ee39db3358d019b9b754d45c8e7964ab4e051。UMI-4/VR-5/Full-14均没有连续无地面接触时段；Full-14左踝峰值12.29mm但仍保持某处足地接触，不能声称摆脚离地。全是0 GPT诊断，不给actor参考/隐藏结果、不计推门成绩。最后使用同一IK关节参考直接作用原生PD做执行链诊断，明确bypass_network_for_actuation_diagnostic，不冒充model_38000策略表现；正式任务仍使用原模型和UMI-4接口。

### R019，水龙头第四条完整记录与控制诊断边界

水龙头episode-0004完整结束：35动作/74.16模拟秒/wall1170.25秒，24到位/11超时、无成功；v3 SHA c7994ae87c924d66feb56974fafa80468cdc573df4f641f976ab80ff1bc10404，744words/6108chars/5346非空白。局部X轴thumb-up姿态可跟踪，但低探和侧探没有确认活动杆运动。failure_review.json保存原因、证据、排除项和下一候选；human_observation_request.json保存末帧双目及部件身份问题供桌面转达，暂不靠猜测重复同一接触。新增host-only机器人-外物接触记录（排除地面和自碰撞），不进入actor packet；7项recording/host测试通过。

ik-actuation-01在同一IK参考直接PD下1.04秒触发失稳，左踝最高37.4mm仍始终有脚地接触；不能将几何IK替换动态稳定器。foot-residual-01在网络上加8Nm有界脚部Jacobian补偿，4.8秒未失稳但左踝仅2.936mm且无整脚离地，不能晋升或盲目加力。正式控制器未改变；下一步优先审查模型输入的可区分响应与原始训练合同，不再重复腕部小参数。

已明确读到USER_UPDATE_20260916_PARALLEL_SKILLS.md：推门为主线，3次门槛后才启动IKEA；现有零模型接续器保留，地面红块与角色研究各有独立写域，SIMPLE supervisor为共享核心唯一发布者。尚无SIMPLE成功，不宣称完成。

### R019，弯腰拾取首轮结束与脚部幅度输入审计

BendPick episode-0001完整turn/skill_update结束：32动作/99.40模拟秒/wall1126.59秒，无成功。v1 SHA8c8d7d5631cd6909486ecfefe3439727db59bd9ed19cda5a78c9f67adb71eab7，741words/5702chars。0.30/0.40闭合使盒子倾斜，抬腕21.6mm时物体回落且手分离，不能算握持或8cm抬起；最后张手撤回、仍站立。失败审查保存，下一轮只检验Astra自提的侧面净空下降/拇指低于顶面的候选；新host接触记录仅用于离线审计。第二账号initialize/thread/start/真实首动作核实，苹果3同样核实。

foot-sensitivity-01固定初态与真实history，执行0候选动作。静态6cm足部上移使网络关节目标的固定base踝FK上移仅0.13mm，20cm上移13.46mm，说明响应非线性，不能当动态成功。现启动foot-amplitude-01仅改变左踝目标8cm/20cm、同0.5秒和初态，检查是否整脚离地；正式actor限幅未改。

### R019，连续四点接口形成短时步进并进入正式接入

foot-amplitude-01仅提高单点脚目标8cm至20cm：峰值从0.198mm升至12.92mm，但始终有脚地接触；主要表现为屈膝/下蹲，不晋升。swing-amplitude-01在既有连续交替参考中提高摆脚幅度，UMI-4左/右脚分别离地0.14/0.20秒，峰值48.23/54.53mm，落地后前移111.54/124.20mm，无失稳；右脚仍未到原目标，不能称通用行走已掌握。

接入可选正式continuous chunk：2–5路点、每段至少0.5秒、总长不超过3秒，整段预检后执行，未来帧跨路点，途中不等待逐点到位；同一chunk固定active集合和夹爪目标，初态与inactive项锚定实测。腕每段6cm/整段20cm、踝每段及整段30cm、姿态每段0.1rad/整段0.3rad，仍保留2m工作域和原失稳停止。默认单点接口完全保留，只有显式启用的推门runner使用新能力。没有把合成参考提供给actor或写入skill；它只是控制诊断。

continuous-api-seed0/6-01通过实际接口、无monkeypatch独立重置复验：两例均0.14/0.20秒离地并前移约11/12cm；seed0物理指标与原诊断逐值一致。seed6保存201帧命名关节状态独立重建接触，也得到相同离地时段，最低骨盆0.7234m、最大倾斜15.887度；这次重建不是新物理尝试。26项接口/host测试、15项原LiveSim回归通过。所有仍是0推门成功。continuous-control-review.json记录假设、证据、排除项和边界；下一步推门episode0006由Astra自行根据新接口规划。

新SIMPLE重置记录真实UUID、boot ID/PID/start ticks、seed及settle后状态SHA，供未来独立成功来源审计；不回补伪造旧记录。推门新回合同时启用此前已验证的原生手指几何。

推门episode-0006正式启动后已核实第二账号initialize、thread/start及首个真实continuous命令，account_route_verified.json保存。该首动为Astra按旧v5选择的右腕协调候选，仍未接近门；不向其注入host诊断轨迹，完整等待其自主回合和修订。BendPick episode-0002路由及首动作也核实。

第二账号额度只读复查account-2-limits-03：ordinaryUsageAllowed=true、planType=pro、通用周期已用23%，0新模型turn、未使用重置券。第一次沙箱网络读取失败保留在account-2-limits-02/infrastructure_error.json，不误记额度耗尽；随后在已授权网络上下文单次读成功。

### R019，推门6／苹果3／拾取2完整结束与段内本体反馈

三回合均完整turn/completed及skill_update，无模型错误、无成功，各failure_review.json保存原因/证据/排除项/下一改变。推门6为3个continuous动作、8.42模拟秒、wall405.14秒；v6 SHA0b8fbf0640f076bc6ddea6d62a396cb9f74f1c102f018f4b5e9b5c7705356c7b，737words/5728chars。右腕侧移未建立接近，连续4/8cm持续抬脚仍不成功；Astra自己提出下一步抬起-落回候选，并要求段内本体证据，不把终点没变当未运动。

苹果3为70动作/226.36秒/wall2723.40秒，v3 SHA552d9abf8c6072e356837d65b3e3e15129bc2bc8c301e63161608c5c07220332，759/6086/5306；终于建立可见预抓，但闭合0/.15/.35/.5及两次18mm抬腕未证明苹果离桌，打开后苹果仍在碗旁。下一候选为高位先确认部分闭合后的对向指面高度和姿态，再下降；不是握持标定。

拾取2为44动作/138.10秒/wall1242.85秒，v2 SHA3625b7e81afe74195d8ee4b3d4d9336905e721422f95d825329d7b07e46439cd，750/5836/5067；侧向进入仍使盒子倾斜、抬腕13.2mm没有保持，下一候选为换手或明显改变姿态。失败未归因单一接触，因远离盒子且无姿态约束时下降也偏差。

continuous反馈新增50Hz公开机器人四点位姿trace、峰值踝高对应样本及位移范围，仅显式allowlist本体字段，绝不含接触/物体/奖励真值。24项针对性测试通过（首轮test缺json import的NameError已纠正，非仿真失败）；待一次实际harness记录校验后启用下一轮。正式推门仍0/10，苹果/水龙头/拾取均0。

continuous-feedback-01实际harness校验通过：1.22模拟秒/62个50Hz本体样本，显式字段allowlist且末样本与最终观测完全一致，无失稳，0任务信用。推门7、苹果4、拾取3启动并完成首个真实动作，三者第二账号路由核实。推门7自主抬起-落回4cm候选的踝峰值仅0.022mm；相同时序腕部对照实际28.9mm，Astra已用公开段内trace辨别终点到位与真实运动；完整回合仍等待。

下一轮推门task spec补充定性探索指导：独立垂直抬脚不是测试有界协调移重/摆动/落地候选的先决条件；小幅无响应后应检验显著不同的幅度/时序/协调假设，并从公开段内本体记录验收，不无限交换腕部小探和同一负载脚脉冲。只说明实验方法，不供给诊断轨迹、数值动作或隐藏真值；当前7轮workspace不热改，也未改写Astra自身skill。见continuous-guidance-review.json。

### R019，推门7完整复盘与关节层公开反馈

推门episode-0007完整结束：3动作/3.54模拟秒/wall356.37秒，无成功。v7 SHA06bcc3c0ac081833955d189c1a23574b7e35a06fd4b9f79850fd12266277cd3b，{'words': 736, 'characters': 6015, 'non_whitespace': 5265}。左右4cm抬起-返回峰值仅0.0224/0.0100mm，腕部正对照28.93mm；三个终点全部target_reached仍没有步进，Astra明确不把其当成功。failure_review.json保存原因/证据/排除项；自提下一假设为同次动作内命名腿关节参考与实测响应的区分。

下一轮公开trace新增机器人29关节实测角及实际送入原生PD的目标角（model_38000+腕PI），与原50Hz四点位姿同步，关节名明确串行映射。它们属于当前自身动作的机器人控制反馈，不含物体/接触/奖励真值；未向actor提供任何独立诊断轨迹。24项针对性测试通过，真实harness记录校验正在执行。

continuous-feedback-02真实harness校验通过：1.22秒/62样本，29命名关节实测/目标数组完整，末帧目标与最终观察一致、无失稳。推门episode0008按v7及新增公开控制反馈启动，日志door-campaign-08.log；苹果4、拾取3仍运行，不热改。仍无推门或其他SIMPLE已审计成功。

推门8已执行首个真实continuous动作（4.00秒），第二账号initialize/thread/start/首动作核实，29关节公开反馈与201样本写入本回合public trace；当前无成功、回合未结束。继续而非启动替代完成。检查点ref/ACCOUNT2_LIVE_CONTINUE_20260916.md及continuation/supervisor-state.json保存，既有接续器与三条正式回合均在运行。


### R019，接续接管与推门8自主步进证据

已完整重读AGENTS、USER_UPDATE、api-budget、R020 inbox及最新ITERATIONS；共享预算10000元、每1500元汇报，API来源/计费未核实只阻塞付费分支。复用既有角色审查，不重建接续器或复制ground-to-table任务。推门8、苹果4、拾取3接管继续，未重复启动。

推门8由Astra从自己的公开控制反馈逐步改变连续参考，第4动作右踝前移127mm、第5动作左踝前移201mm，但伴支撑滑移。独立对已保存前1140帧（截至第6动作）重建整脚接触：左右各最长0.26秒无地面接触，最低骨盆0.731365m、最大倾斜14.840度。支持当前自主动作产生短步进，不能推广为稳定行走或任务成功。此为host-only已有状态审计、0新增物理尝试；未向actor提供接触真值/诊断动作。证据door-0008-motion-audit-01（先假设与区分标准，再执行、结果和下一决定）。正式推门仍0/10，完整回合等待。


BendPick3完整结束：52动作/200.72模拟秒/wall1870.78秒，无成功，完整turn和skill_update；v3 SHA05018077b7f1e550f5944d598b3f134794d6e66cb80b28939db6f20e666f7499，777words/6101chars。换左手、高位进入仍没有对向保持；闭合使盒子倾斜，抬腕/保持后盒子向桌前缘转落。failure_review保存证据和排除项。下一轮复用自身v3验证更平的姿态与入场轴，不把包围盒重叠当抓持。


苹果4完整结束：63动作/162.92模拟秒/wall1978.07秒，无成功，完整turn和skill_update；v4 SHAe928192894891e11ca4ca6386943461bf08581e6e6331f52ca8ab5abe5d407c5，754words/6112chars。较短路线获得双目可见预抓，但4次闭合/抬起（.48/.48/.58/.65）均未确认离桌；末帧苹果仍在碗旁。failure_review记录。下一轮自行用可见对向曲面代替未标定包围盒中心，并隔离偏移变量。BendPick4首个真实动作及第二账号路由已核实。


### R019，推门8完整结束；证实并修复固定门框虚假碰撞

推门8：17动作/66.08模拟秒/wall1711.98秒，完整turn与skill_update，0成功；v8 SHA6141ceddca0914094aa84083ee3c56131f55fa0bdec7e5c88116b721ed588cae，713words/6075chars。Astra自身连续参考使双踝累计前移584.6/547.0mm，随后双手接近均停滞。host记录只接触固定link_0而非活动link_1。

只读审计证明source frame mesh单块凸包填住门洞：记录接触点距原始三角面148.15mm，距凸包面0.123mm，原始mesh射线无交点而凸包有两交点。门框source有16顶点，是厚度恒定的矩形环。RSI内新增simple_door_collision.py，按原始边界精确分4个box，保留原视觉/惯量及叶片/把手/铰链/接触参数，不改原文件；仅显式--door-frame-override启用。

第一组同进程第二reset干扰物变化，状态恢复拒绝，保留invalid对照；改为两个独立进程同seed，351x80站立qpos逐值差0、均无失稳；旧记录点虚假frame接触消失，独立几何+50mm反事实仍保持同深度的活动叶片接触。反事实不执行策略、不计成绩。证据door-collision-audit-01、door-frame-validation-02-original/fixed、door-frame-override-review.json。新成绩需明确标注碰撞表示修复，不能声称原封不动native benchmark。下一完整重置复用Astra v8并重新审视接触假设。


BendPick4完整结束：28动作/113.16模拟秒/wall1008.56秒，无成功、完整turn/skill；v4 SHA1307440c2b3eec59d58f2cf0b536017126b143a587270bf48a41262db305695c，765words/6118chars。右手低位姿态与浅对向仍失败，进入使盒子偏移后张手撤退。下一候选改变抓取轴。

完整机器人手部碰撞几何已验证：16链接/18几何，静态body-local凸碰撞mesh侧文件约1.85MB，每帧只给路径/hash和实测链接位姿，排除物体/接触/奖励。真实闭合1秒后局部顶点差2.78e-16m，位姿正确更新，无失稳。hand-geometry-detail-01保存公开几何、观测和诊断视频；0任务成功。新回合通过HandGeometryProvider启用，不热改当前door9/apple5。主skill长度不增加，task_spec说明按需用Python读取。


接续检查点：door9首次真实活动门接触，当前最大开角7.706度，未达30度/1秒条件，不计成功。apple5、bendpick5均真实执行，第二账号路由核实；bendpick5完整机器人手部sidecar已实际暴露。account-2-limits-04只读检查ordinaryUsageAllowed=true/pro通用35%，0模型turn/0重置券/0付费API。最新handoff与supervisor-state=continue已保存，不重复启动在途回合。


最新HUMAN_FEEDBACK交接已完整阅读并ACK：用户要求停止额外额度/余额/费率调查，主控此后不再查询。另一API协作分支已确认校准3.39元，旧全任务0付费说法过时；本主控未发付费请求。人工求助只针对至少3可比较自主失败，视频优先，H001-003按抓法条件化包夹判断，禁止统一掌心等高。已有H001复现完成、纠正trial1在独立写域重建prefix，不重复启动、不计正式成绩；status旧待澄清字段已被003取代。当前主线三个在途Direct回合未热注入反馈。


### R019，抓盒5完整失败与新接续ACK

完整重读AGENTS、PARALLEL_SKILLS、HUMAN_FEEDBACK、api-budget、R020 inbox和最新ITERATIONS；不重复旧IK对照，当前门9/苹果5继续。抓盒5完成25动作/87.28模拟秒/wall857.56秒，完整turn+skill_update，无成功。v5 SHA6bb8a2841612285e5f0c2a8cb4441bd95435e3609b9da85df2e77e957c022b6e，745words/6114chars/5349非空白。右手目标yaw未实现，下降时pitch逐渐变陡，未建立低位对向；025张手撤离。2183帧/87.32秒视频完整。failure_review保留证据/排除项，下一独立重置检验Astra自提左手、低位先行、固定姿态纠正；不晋升共享skill。


苹果5完整结束：72动作/186.66模拟秒/wall2032.18秒，完整turn+skill_update，无成功。v5 SHA879c4f8b4e2cffbbb0fdd59c1d73d2b19badb63064ff3c04a8555ddaa4ae4f2c，756words/6126chars/5347非空白。高位局部X旋转可跟踪，低位/后置pitch修正饱和；3次闭合抬起与独立保持均未确认离桌。末帧苹果仍在碗旁，4667帧视频完整。failure_review保存；下轮使用已验证全手部表面，保持自主Direct，不热注入H001反馈。

水龙头5恢复独立正式尝试：新增native runner显式--continuous-chunks复用已验证同一SimpleLiveSim四点接口，默认仍关闭；不提供步态/物体轴线/隐藏真值。新假设为协调换位获取无遮挡视角，和先前单点脚请求失败区分，native-continuous-review.json先记录标准。2项continuous控制测试通过；水龙头先前完整turn与skill确认，无重复在途环境。


### R019，推门9完整：真实开门16.56度，仍0/10

40动作/156.68模拟秒/wall2457.71秒，完整turn+skill_update，0成功。v9 SHA24dacf472ac0e01e050f46a3c167f17f24265d48d1cc284fb32e56e3ef623ac6，702words/6008chars/5290非空白。host最大相对开角16.555729度，有活动门手接触；3918帧/156.72秒录像完整。整7835帧重建左右最长整脚离地.26/.28秒，最低骨盆.72803m、最大倾斜14.995度，全程站立范围内。晚期action40右脚未整脚离地，左支撑后退约158mm，不能继续同样受载大幅推腕/举臂补步。failure_review与door-0009-motion-audit-01保存证据、排除和结论。下一轮依Astra自身v9先在低臂位建立更近、更平衡支撑，然后再接触，不提供host真值。


### R019，水龙头5基础设施故障：3秒浮点边界修复

水龙头5真实执行仅1动作/4.4秒，后续合法3秒chunk在时长差计算中成为3.0000000000000018秒；运动已登记但夹爪校验拒绝，残留active。旧host误标为可重试并自动续turn，最终27个完整turn但仍仅1物理动作。一次性边界观察器只在确认所有turn/start均完整completed且无在途推理时停止空闲app-server，infrastructure_boundary_stop.json保存证据；未截断推理。原result保留，正在用同一Astra policy harness第二账号做该回合terminal review，无新增物理/新campaign。

修复：按相对段时长fsum计算，避免绝对clock相减溢出；LearningHost对登记后异常/物理已推进异常明确终止环境、取消待执行命令、允许完整skill_update，不再以no_execution可重试掩盖。18项测试通过。真实同seed回归02，两动作2.4/3.0秒均完成，合计9.4模拟秒，active=None，无新模型/任务信用。回归01误用抓方块默认手几何，0动作初始化失败保留，修正diagnostic几何provider后才通过。证据continuous-duration-fix-review.json。推门10已采用修复的新加载代码并真实执行；苹果6/抓盒6仍原单点接口，不热改。


### R019，首个独立推门成功：episode0010（1/10）

完整turn+skill_update+独立host审计通过：18动作/66.84模拟秒/wall892.36秒，1672帧/66.88秒视频。复用现有R020 audit_trace，3343连续ticks、真实手接触414样本，最大/终态开角30.095595度，连续条件1.54秒；最低base.711672m、最大倾斜15.13996度，全程站立。reset UUID/seed10/进程身份独立，18唯一模型动作，非回放/诊断；success_review绑定证据hash。v10 SHAce7ba5c1aba6536af706fdf4ee73d16e31c062d5d8b8e5e7416129f0073a345b，714words/6077chars/5347非空白。先低臂接近并补齐支撑，再右手高位张手连续推动，成功候选仅本任务，不晋升共享core。明确修复门框碰撞的MuJoCo推门变体，不称原样native CloseDoor。下一独立重置11继续。

IKEA仍未启动，真实物理审计1/3；R020登记因original_physics字面条件待既有维护者纳入明确override版本。向用户给出的rsi-skill-review-0916会话名排队失败（No active session found），frame-override-coordination-queue.txt保留，不能声称送达或伪造original_physics=true。

水龙头5已补完同一episode终止复盘：新增1个完整Astra/xhigh terminal-review turn、0物理动作，v4 SHA660926af46eb7bd483db4cc2743c00d1ee726f3d8dc2e4663069288264f70611，712words/6061chars/5332非空白。原result已单独保留；infrastructure_review明确1真实动作/4.4秒、27原完整turn不等于27尝试。接口修复已通过正规队列转交既有ground-to-table主管（仅入队回执，不冒称阅读）。


最新用户纠正ACK：旧未达标回合必须区分主动提前结束、预算、安全/物理终止及基础设施中断，不再笼统称真实物理失败。检查时另一工作区写者已把finish_attempt改成只记录停滞并继续；主控保留该修复，补齐任务说明/运行时优先合同和原生成功/失败/预算/基础设施回归。20测试通过（termination-and-duration-tests-02.log）。首个本地测试mock缺latest_path无效，原日志保留不冒称旧bug复现；door8原17动作/66.08秒/剩余173.92秒却返回rollout_finished的旧回执已单独绑定哈希。原始episode不回写，ledger按termination_class分层。

已读H001-004原话与作用域，后续正式苹果须--human-feedback human-feedback/H001-user-feedback-004.json。native runner冻结原话/规则/hash/采用时刻到task_spec，并记录human_feedback_used=true/human_demonstration_used=false；当前apple6未提前伪称采用004。侧抓先建立张手包络、看不清不靠小闭合探针，不推广成顶抓统一掌心等高。


### R019，抓盒首个审计成功与苹果反馈分层

BendPick episode0006完整turn/skill更新，63动作/205.28模拟秒/wall2595.16秒。独立审计确认1次真实成功：盒原点升高86.639mm，原生reward.861445；906个抬升样本均有对向承载接触，末17.3秒无桌面/其他支撑，末盒底离初始支撑面76.393mm；最低base.718807m、最大倾斜11.42088度。原生阈值末段2.54秒，但没有额外终态hold动作。5133帧/205.32秒视频完整。success_review及bendpick-0006-audit保存，离线重建不增加尝试。v6 SHA a6d9fd159062efacacc598a09e438a1151669691cadd4bef95381fecdff64152，740words6115chars5352非空白；共享core未改。

苹果6完整结束93动作/223.54秒，无抓持/放置，属于旧合同下policy_early_stop，非原生终态物理失败。四个闭合/抬起测试均未保持，5589帧/223.56秒视频。公开首次selection已披露H001语义反馈暴露，故human_feedback_review与ledger纠正为反馈暴露，保留原始result；未冻结具体版本，不能冒称已采用004。v6 SHA963e38139e6e4ff7e1c5705c4df0cfb05954bec10007c221bb98923f95903abe。新独立苹果7在07:30:26UTC冻结H001-004/hash2aa49674accf01bb4229aa4215b8b178b9261d99d1c1d40b758368e6f46ef696，并采用非终止stall合同。

新的原生抓盒放置任务已完成语义/原生准则/既有可用性审查：boxplace-task-entry-review.json；盒-篮接触且无手接触不等于正确入篮，终态需另审。复用已完成native preflight，不重复环境诊断。新增受审查任务候选manifest，只准公开版本/rollout路径、校验版本hash和负迁移边界；3相关测试通过。既有BendPick v6与自身公开rollout供actor自主选择，不给host真值、不迁移tracker状态、不晋升全局core。boxplace首轮使用第二账号既有policy harness、连续四点能力；不同于独立ground-to-table任务。


### R019，推门第二个独立审计成功（2/10）

Episode0011完整结束28动作/105.02模拟秒/wall1056.61秒，v11 SHA634952e48aba3402b3da04b5cb69a6c15306e1d86cc7fe46d55d02c2d5ca1769，695words6065chars5353非空白。复用R020 audit_trace核验5252连续tick，最大/终态开角47.812861度，达标连续2.70秒，手接触764样本；最低base.711942m、最大倾斜15.13996度。2626帧/105.04秒视频完整；reset UUID/seed11/进程身份与上一成功独立。success_review保存完整证据hash。

本轮改变初始对齐后自主使用左手；高位推到停滞时finish_attempt返回false，并继续动作19，后撤/降手卸载、补近站位，再抬手推动成功。证实非终止停滞合同在实际任务有效；不把更近站位/手姿/初态混杂解释成单参数因果。所有正式控制仍UMI-4、checkpoint PD、明确asset003-exact-frame-four-boxes-v1，非原样CloseDoor。工具review_completed_door_episode.py只复用现有审计并生成host报告，不复制/修改R020门槛组件，也不自动登记IKEA。下一独立reset12继续。


接续检查点07:43UTC：推门12、苹果7、水龙头6、抓盒放置1均已有真实动作及第二账号Astra/xhigh路由核实，完整回合继续等待。四个唯一tmux与证据已写入supervisor-state=continue及ACCOUNT2_LIVE_CONTINUE，旧文件归档到supervisor-handoffs/20260916T074354Z。既有R020维护thread01a0a87f-f806-7883-9648-190e49447d86已精确ID入队门框版本审查请求（message01a0a927-e682-7f41-9d49-5ea32bfcd853），仅入队未见ACK；未改其组件/新建通用代理。

H001有界3诊断已只读审查：1闭合测试按003、2预抓预算结束按004，不能当3同因004抓持失败，formal信用0。继续现有全预算apple7，不追加第4诊断或用户追问；详见h001-bounded-transfer-review。未来native录像按human semantic feedback显示，scene_setup保存反馈来源；已启动apple7旧通用Direct页眉用video_label_note纠正解释，原录像不热改。


### R019，推门第三个独立审计成功（3/10）

Episode0012完整turn/skill，31动作/113.96sim秒/wall932.34秒。5699连续ticks，终态35.873019度、达标连续2.42秒、588手接触样本，全程站立，最低base.714384m、最大倾斜14.99523度；2850帧/114秒视频完整。reset seed12/UUID/进程与前两轮独立。v12 SHA15e9f2ec522a9325d20ee9fbd371f21b9b3ea9e7ae32312efa10d6787e6da092，675words6045chars5353非空白。高位推动遇限后记录stall继续，自主低臂卸载/改变补步/重新校高后成功；抬臂时被动足漂大，不能称稳健通用步态。正式第13轮继续，IKEA达到用户3次物理审计前提，开始只读场景核查，付费仍须现有共享预留。

原R020维护线程已确认无在途进程后以同thread恢复一次门框版本审查，未新建通用agent。其最新门槛交付尚待完整结束消费；未伪写original_physics。R022旧finish缺陷有效单测复现和23项整合测试交付已只读复核补入termination-contract-update，生效边界不变。

抓盒放置1原生成功被任务审计否决：22动作94.94秒，动作022仅.35闭合，未lift/transport/release。原生标志65个样本为true，终帧已false但evaluator曾经成功被锁存；盒最高升20.12mm，终态仍篮外，2374帧录像保留。success_review/failure_review明确0任务信用。新native runner给actor的successes_so_far只用已审计成绩，并分开native_criterion_successes；实测既有boxplace1为0、bendpick6为1。下一boxplace2仅改变自主篮缘净空假设，同控制器/原生准则，避免一次问题就扩大控制诊断。


### R019，第四次独立推门成功；R020三次门槛已正式登记

推门13完整34动作/130.86模拟秒/wall903.38秒。独立host审计开32.02805度、保持1.64秒、743手门接触样本、最低base.71250m/最大倾斜15.13997度；3272帧130.88秒录像完整。累计4/10，v13 SHAac59414834a055a8848422f04a2d2f50aa4323f99892de9674244f43b0f2daa6。两次finish_attempt均只记录停滞、立即继续，最终成功；踝峰值不等于整脚离地或可泛化步行。下一独立14不提供host真值。

既有R020维护者完整交付schema2并结束turn，41项离线测试不计物理成绩。主控核实并签发10/11/12真实收据，physical-gate-state显示3次独立审计通过；明确original_physics=false及固定门框修复ID。IKEA仅已开始只读资产解析，无该任务物理/API成绩。

水龙头6完整64动作241.10秒物理预算结束，无成功，6028帧视频完整，v5 SHA b2ff63d0f262acc3f74be62f4c29e34b795b9750e9ba79d2e94db85dd6e6c929。7轮新重置提前检验自主换位观察候选；不共享实时状态。抓盒放置2仅3个张手动作15.02秒再次触发原生接触成功，host审计否决，仍0成功。两反例触发显式staged-placement门槛修正；原始结果/奖励/物理保留。


抓盒放置3起显式--verified-placement，新增host-only acquired lift(.05m/.5s、同手拇指+对向承载、无外部支撑)后released native-qualified container support(1s)门槛。掉落/桌支撑断开阶段连续性，仍另审最终几何；不是原样native benchmark。原奖励/布局/物理未改。两旧假阳性按原记录高度/native时序即被排除（接触取有利假设，不称全动态回放）；5针对性测试+2录像回归通过，真实native seed3初始化和25ticks集成通过，0任务信用。review与边界在placement-gate-review。door14/apple7/faucet7已加载代码未热改，boxplace3已实际动作并核实第二账号。

IKEA在3次门槛后只读检查：现有ds4090 USD22.11拒绝Unicode家具prim名称，两文件均打不开；日志保留，不称源资产坏。已用本地既有匹配Assimp5.4解析FBX：469节点、141未后处理mesh，两扇卧室门与把手分离，原文件不改。根据TV材质/柜体所在西墙，Door_West是用户照片右门候选，待派生静态预览确认。FBX不证明USD关节/锁舌，也未开始IKEA物理/API；不安装资源，不查额度费率。


推门14第五次独立审计成功：23动作92.62秒，开36.115905度、保持2.88秒、879手门接触样本，全程站立，2316帧92.64秒视频完整；v14 SHA5c1ca23b1be27271a1409942fef57e5a70d0664c21f63125bb80db2779d7ee36，667words6022chars5336非空白。新重置15继续。当前计数按明确completion_contract分层，host success不再笼统列成原样native benchmark；历史result不改，raw native flags仍在host trace。


IKEA派生静态预览完成：preview05确认电视/柜体/右门空间对应，目标为Door_West；141原FBX mesh转换，原图像解码RGB等像素PNG副本及UV原点转换均在RSI。未运行physics/robot/model。原FBX门闭合，用户图半开；材质/光照/地面显示非完全一致。preview01平面惯量、02纹理格式、03相机朝外问题与04/05修正各保留，不算任务尝试。艺术家门pivot(.000038,1,13.499997)原FBX单位及把手pivot已只读提取，尚非验证的物理铰链/锁舌。下一步新RSI物理适配，不重装工具、不改源USD/FBX。


### SIMPLE最新分工与框架候选ACK 2026-09-16T08:45:05.750925+00:00

已完整读取SIMPLE_EVAL及HUMAN_FEEDBACK末尾和用户指定文件。ARCH-REVIEW-20260916-V1 ACK；接受先压缩/归档入口再启用实际skill+runtime上限。保留非终止stall、故障原子性、verified-placement与分层账本。当前物理收益未验证。IKEA已有门槛/资产证据交给FRAMEWORK_OUTBOX，不继续新增执行。memory-priority/progress-ui既有协作者不重复。


苹果7完整预算结束：122动作240.18模拟秒，四次局部闭合/抬起未保持苹果，末帧仍在桌上旁碗；0成功。H001004已冻结，非无辅助Direct；四次probe不算四次独立失败。v7 SHA1cf4660255764a584d65130c17b9de41bf6908e1060e8909e0f5b77172830c1a，全turn与skill修订完成。failure_review保留视觉证据、排除假设、相机投影待核查与下一开放手深度/侧向检验。


水龙头7完整61动作240.06秒预算结束，0成功。v6 SHA76fcd8e69154be4173f9e418792cd7e4c8dc4b86a47bbb533b11aa14aa57823c。公开图像报告活动上片偏转但伴随支撑漂移，因果未定，不能回放该不稳定动作。抓盒放置3也完整52动作241.92秒预算结束，全程张手、未获包络/抓持；新增明确完成门槛未误报成功。两份failure_review保存完整修订/视频与下一项改变。


相机合同诊断：苹果7公开经验触发核查，发现SIMPLE显式内参与视频宽高下的渲染视锥不能由对称fovy近似。实际头目fx606.30/fy454.72/cx309.23/cy189.48；旧只用fovy会报告fx=fy454.72/cx320/cy180。已知独立标记渲染误差新合同<0.75px、旧合同有>10px；普通fovy不变，2渲染测试(2分辨率subtests)+9既有policy测试通过。native两相机零actor动作集成通过，reset自带.005秒明确记录。新render_intrinsics仅相机信息，pixel_to_plane用实际内参；不改图像/物理，无任务信用。在途仍旧代码，后续新回合才能加载；不能据此归因所有抓取失败。


### 重启恢复 2026-09-16T09:58:29.738114+00:00
当前boot102fa58c与door15原boot3d81b4d6不同；宿主核查旧SIMPLE actor/watcher全消失，唯一rsi-simple-recovery-0916/PID292946。door15保留61动作、最后预算ACK，但无完整turn/result/skill_update，登记基础设施中断；MP4缺moov不可解码，原文件保留。不得补造v15。门仍5/10，BendPick1，apple7/faucet7/boxplace3均完整预算0成功。
ARCH长度/MEMORY-PRIORITY已逐hunk发布；所有入口先归档压缩，原memory不变。相机render-frustum-v1已测，新reset才加载。NT候选ACK：先应用turn/start无期限等待与不确定提交锁；闭合网络失败自动续接待与每turn审计文件整合，不冒称完整部署。3预算+18检索+7记忆测试、adapter/host/placement相关回归通过；首次系统python缺scipy属环境调用错误，日志保留，现有SIMPLE解释器运行通过。
watch基线fixture有效复现旧session绑定导致重复resume(另缺新函数的Error不是原bug复现)；修复绑定当前boot/PIDstart/session/log，2新+6旧测试通过，准备唯一watcher等待本recovery自然结束。


恢复后四个正式reset已实际执行：door16/apple8/faucet8/boxplace4。app-server thread/start真实回执均account2/gpt-6-astra/xhigh，发送developerInstructions SHA与policy_instruction_budget逐字一致，组合5846–5893chars且三项上限全满足；四者首观测双目均含实际render-frustum-v1内参。完整turn、受限skill_update和任务审计仍等待，不能以首动作冒称成功。现有唯一watcher锁定recovery tmux、native PID/startticks、boot与当前日志，model_calls=0。


### R019 recovery 2026-09-16 10:14–10:20 UTC：两项完整物理验收

门16独立审计成功，累计6/10；25动作96.36模拟秒，32.681°、连续1.64s、618接触采样，完整turn、v15、2410帧视频。水龙头8首次独立审计成功：11动作31.38s，活动关节-0.799896rad，逐控制步复算原生双调用reward一致，785帧；持续手接触下成功，撤手保持未测。ARCH长度+MEMORY-PRIORITY及相机合同通过这两轮完整调用链，修订总长door793/5939/5132、faucet811/6067/5242，未超上限。混合改动与新reset不能单因归因。

门17已独立新reset；水龙头最低验收完成后不重复开，空出的并行位交给已预检的原生OpenOven首轮。新spec及transfer来源仅公共版本/rollout，显式拒绝照搬推门方向、世界坐标、持物行走。苹果8、放盒4仍完整推理，未中断。共享core未改。证据：各success_review.json、instruction-cap-integration/status.json、public-atomic-experience-20260916.json。

### R019 权限合同偏差 2026-09-16 10:20 UTC

真实thread/start回执发现actor继承readOnly且approvalPolicy=never，仅审批reviewer为auto_review；未满足用户明确workspace-write+自动审批。未热改/终止door17/apple8/boxplace4/oven1。先本地schema核实、红灯复现，再最小设置sandbox=workspace-write、on-request+auto_review并在turn前校验回执；9项测试通过。第二账号零模型turn握手确认workspaceWrite、仅agent运行根、networkAccess=false；证据recovery-20260916/permission-contract-fix.json及permission-handshake/result.json。下一新reset生效，未改run.sh或账户配置；无额外额度/价格查询。

### R019 recovery 10:27–10:34 UTC：门7/10、放盒与烤箱验收

门17：34动作119.24s，39.802°、4.74s、781接触采样；v16及2982帧视频完整，累计7/10。两次卸载/补站位再推，未提前结束。门18已新reset，首次实际加载显式workspaceWrite/on-request+auto_review；旧在途未热改。

放盒4：51动作230.28s，完整v4；强化连续抓持/抬升/搬运/释放合同通过。逐记录重算时序，最终无机器人或其他支撑的篮支撑2.8s；独立保存状态几何重建终态仅接触brasket且COM投影在篮轮廓内，视频5758帧。盒高于篮边，不宣称完全容积包含；无独立退手动作/持物行走。旧两轮native假阳性不改账。

烤箱1：14动作53.44s、1337帧、v1，逐帧原生双reward复算一致，joint2最终1.57196rad；终态无外部机器人接触，双目可见开启门板及炉腔；独立审计1次。水龙头8/放盒4/烤箱1最低验收均完成，空位依次给烤箱、垃圾桶、办公椅；后两者仍待真实验收，苹果8继续H001004。库存91入口由audit脚本按原台账同步，门变体不抵扣CloseDoor。新公共原子候选见public-atomic-experience-20260916.json；shared core未晋升。

### R019 recovery 10:39 UTC：垃圾桶验收及进程分层

trashcan1五动作16.62s，完整v1/416帧视频；原生角>.5与reward>=.9逐控制步重算通过，最终.533603rad，桶身最大位移12.445mm，稳定站立，1审计成功；撤手保持未测。宿主tmux readonly核实主管PID/starttick/boot一致及精确SIMPLE watcher1个；工具/proc命名空间不可用于认定宿主死亡，泛watch.py误纳其他owner的首份核查保留并已纠正，未动任何进程。ref/ACCOUNT2_LIVE_CONTINUE已归档旧5/10/IKEA旧分工并更新为当前SIMPLE唯一职责。


### R019 10:52UTC：门8/10与NT逐turn审计集成

门18完整28动作105.74s，39.432614度、达标2.94s、577手接触、2644帧视频，v17 SHAae82e3f92849c895970c0fb820f7696d7a147bc2a6c93926eeae5eea9a0bf5b2，独立审计通过。NT-AUDIT-20260916-v1 ACK并在该自然边界逐hunk应用三文件，保留权限/长度/相机/库存修复；63针对测试通过。首次41回归中的Python3.10测试loader未绑定parent模块导致1 error，修正测试loader后41通过，原日志保留；无实际服务额度异常。门审查调用统一turn_completeness，物理准则不放宽。苹果8/椅1冻结版本不热改；门19新reset生效，真实网络恢复收益尚未验证。


### R019 10:56UTC：苹果首个真实审计成功（H001辅助）

苹果8完整117动作238.30s、5958帧，H001004冻结，无动作示教。保存状态几何逐11915控制步复算原生接触奖励零差异；最大原点升高.11326m，承载对向指支持且离初态>2cm最长14.22s；终态苹果全部水平投影在碗轮廓内，边界余量24.66mm，仅接触碗、无机器人接触。公开终态双目显示在碗内，v8 SHAb4a4a351282498bd9e02a7c9bfe3800f7452515d6ccc9879a5151836a04689eb。原生结束发生在释放动作，终态仅.06s记录，不冒称撤手保持或满体积容纳；不作反馈单因归因。只登记本原始物理回合成功，几何重建无新成功信用。门19/椅1继续；新增原生XMoveBendPick首轮，复用公开BendPick6抓取与door18空手接近候选，未晋升core。


### R019 11:04UTC：门9/10与办公椅首个成功

门19完整18动作65.54s，39.362056度、达标2.54s、203接触采样，1639帧，v18 SHA0052b3114edd12601e333b804a9fb350e62167077aa92afe3e36374205b3f280。新codex-terminal-sequence-v1端到端审计通过，含完整skill_update总预算828words6192chars5350非空白；仅单turn自然完成，未发生真实网络恢复。下一独立门20，入口剩余长度很紧，不追加说明。

椅1完整38动作139.64s、3492帧，原生初始参考经独立同seed诊断reset全qpos/qvel hash一致后读取；逐控制步复算原生双reward无差异。朝桌X位移.823940m，距桌2.00445降至1.18007m，椅最大倾斜.08596度；机器人最大21.9945度仍站立。终态持续手接触，无撤手保持；滑移和yaw跟踪失败保留，不能晋升通用gait。v1 SHAde7c726a58baf28d683c90ba1896880d01cf829f64cc392208c766d4107c757b。


### R019 11:16UTC：XMovePick首轮稳定性停止

首轮28动作113.44s，完整NT终态/skill_update，非推理截断；全程闭合0，无抓持。最后双踝升高/双腕降低假说在.88s触发diagnostic_stability_stop，倾角25.0709度、终态base.70128m（全程最低.57715m），不称跌倒或摩擦抓取失败。新v1 SHAe0cde763b8182dc33e28103bd8b64e21f841b2a2e41ae92770c55e69873077f1保存失败证据、排除项、下一低桌姿态/全手净空/非活动臂监测；未验证下蹲primitive不再复用。新reset2继续同合同/H001004，并变初态不作单因归因。


### R019 11:26UTC：推门10/10独立审计门槛完成

门20完整39动作135.74s，42.098949度、连续2.12s、703接触采样、最低base.714459m、最大倾斜14.99524度，3394帧视频与NT完整终态序列通过；v19 SHA887db721d25299fcd09643b89e256b3f92d72a7637bcd1ba7c8a8244babf7baa。真实成功episode10—14、16—20，10个不同reset；20总物理尝试中10成功、8旧主动提前结束、1旧预算结束、1重启中断。ten-success-milestone.json绑定原审计hash。明示asset003-exact-frame-four-boxes-v1推开变体，非原生CloseDoor，不计诊断/回放/中断。不同skill逐轮学习，不称固定policy成功率。不会为门配额再开21；当前三个抓取继续，并把空位给下一未尝试操作任务。全部SIMPLE目标尚未完成。


### R019 11:36UTC：XMoveBendPick首轮完整预算复盘

49动作241.26模拟秒，完整NT终态与v1（SHA755a6ded216f675ea50882c79479e6a172d581d5ffbfa362f32e37691dc4a692），6032帧/241.28秒视频可读。全程夹爪命令0，46超时/3到位；左/右踝前移.46935/.37086m，但无全足离地或通用步态结论。0018及0049原双目确认盒被碰倒后仍平放桌面，无包夹/抬升。failure_review排除推理截断、闭合抓持失败和完全不移动，下一新reset使用任务v1核查卸载站位、全手运动净空和active-set效应；仍无单因归因，不纳人工求助三失败。新XMovePickSimToReal1已独立启动，等待首动作路由；机器人稳定性候选仍由既有框架工程线程准备，未热改。


### R019 11:44UTC：XMovePick第二轮完整预算复盘

49动作241.30模拟秒，完整NT终态与v2 SHA0ca0ea4d582c6c9f3242913346f1a62c30c84ceefb820c5bbabb6d70f75505fd；视频241.320000秒/6033帧可读，0成功。侧抓1—31张手；32明确转为远离对象预成形.35的斜顶抓可行性探索，维持至37后38重开，未建立包络/最终抓持，不称H001侧抓条件已满足。原始031/032/036与终态049双目已阅，苹果仍在桌上。37左臂回收后向后移动并延续到38，39前向参考止漂；耦合未分离，不复用成恢复primitive。保留预算/辅助分类、失败排除和下一检验。机器人稳定性观测候选尚在既有线程离线验证，之后自然边界审查，不热改其他三在途任务。


### R019 11:48UTC：BendPickSimToReal首轮完整预算复盘

65动作240.46模拟秒，v1 SHAdc781d16dee03e8f9b41149885b0dd447fc7b698b5bfe0a89671d48d63e4718b，完整NT终态，录像240.480000秒/6012帧；0成功。多组.35/.40/.45闭合、小抬升及独立保持均未验证抓持；这是一回合内探索，不凑独立失败数。原036左目和065双目显示盒倾斜/移位、部分裁切，无明确离桌保持。actor公开自评035未审查计算输出即执行，因果仍待分离；v1加入计算→审查→执行、全手净空和位移后重新投影。保留所有原证据，后续新reset才加载改进。


### R019 11:51UTC：ROBOT-STABILITY-OBS-V1发布及首动作核查

源hash匹配、两文件77行逐hunk发布；20针对检查通过。首测试副本缺evidence临时父目录引起8个FileNotFoundError，保留后建目录重跑通过，无实现改动。XMovePick3新reset实际root映射body1/world/freejoint地址0，命名高度等同旧qpos2；只对该实例成立。首动作251样本新增本体字段与原记录机器人姿态逐时间匹配，高度差0、倾角差<1e-12度，动作内摘要重算一致。新静态入口预留809/6164/5340，第二账号/权限/相机实际核验；旧xmovebendpick2/xmovepicksim1不热改。完整回合和任务收益待测，shared core未晋升。证据robot-stability-integration-20260916/status.json及first-action-physical-verification.json。


### R019 12:02UTC：CloseDoor原生目标入口审查

推开10/10已完成，不重做；新增关门任务单列。原生角判据joint1<-.16rad、reward累积原样，原随机打开初态与布局保留。asset003同源门框凸包填洞缺陷已有隔离证据，因此仅复用四框条碰撞修复，不旋转push侧、不强行设closed状态；显式native-close-door-exact-frame-v1变体，不能称未修改原生benchmark。native backend/runner新增默认关闭且仅CloseDoor可启用的选项，3路由隔离+2真实mesh质量/惯量/碰撞回归通过。三在途旧进程已加载版本不热改；新CloseDoor首轮才生效。任务细化与公开来源已保存，独立审计要求手实际交互使初始开启门关闭，不认可被动自闭或初态满足。


### R019 12:09UTC：XMovePickSimToReal首轮独立验收

38动作135.54模拟秒、3389帧、完整NT终态与v1 SHA9243384c90379c159f82607f3779b4f86649835fe2b370913364e4f161a29bee。无人工反馈/示教；同seed独立几何reset全qpos/qvel hash一致，保存状态逐6778样本检查全部native成功判定与3cm高度门槛一致。最终盒底升高40.002mm、仅手部接触，连续承载对向指/整盒离桌6.8s；独立保持037为1.5s、最小盒底离初态20.122mm。无post-threshold额外保持/持物行走结论。首次奖励精确复算assert失败保留：637数值差异最大0.002023奖励（0.2023mm等效高度），源码native用mj_step后的xpos、重建用mj_forward后qpos，采样阶段差异为推断，未保存末子步qvel/xpos不能声称精确复算。success flags全一致、独立几何/原始承载接触与视觉证据仍满足验收。BendPickSim2准备仅追加公开v1/rollout检索来源、保留原manifest与任务v1，下一独立reset检验适用性，不归因单变量、不改shared core。


### R019 12:14UTC：XMovePick3辅助抓苹果独立验收

31动作150.44模拟秒、3762帧、完整NT与v3 SHA1e3e446f8330b4bba1d60483476614b065a9fd27b213a2349d15459a312510ee；H001004语义辅助、无示教。独立geometry重建7523记录，same-seed初始化全qpos/qvel一致。苹果底部升高106.946mm，原点108.582mm（native9cm门槛），无非手支撑且承载对向指连续11.26s；030独立保持实际4s、全201样本成立。原始0030/0031双目支持。692奖励数值差异及7399单样本成功门槛采样偏差保留，不能称奖励精确复算；native xpos与post-integration qpos采样不同，最终两者均达标。ROBOT-STABILITY-OBS-V1首次完整物理/skill_update通过，组合810/6158/5333；初态/skill/反馈混杂，不能单因归功于本体字段。该轮无独立post-threshold保持、无持物行走。推门10/10另9操作入口验收；shared core未改。


### R019 12:22UTC：XMoveBendPick2完整预算复盘及下一重置

58动作241.86模拟秒、6047帧；完整NT/v2 SHAec26660b1bc885a96572b75d339d7ec9f655e1710f29ddb07bc970fd0bdada48，组合751/6101/5332。45超时13到位，踝各前移约.322m并有yaw漂移，不称通用步态。048/049浅包夹.10→.20使盒位移；053张手重新进入再次碰倒。后续自由通道姿态/下降测试改变可跟踪范围，但真实进入仍偏离理想刚体扫掠；无抓持，预算截断不作终态物理失败求助。首skill_update含agent域证据被拒后自行纠正，原两次回执保留，不补造。新reset3才用v2、已发布root观测和公开XMovePickSim1姿态/包夹保持候选；明确高桌与当前低桌几何不等，拒绝坐标/闭合复用，无单因归因。

MobilePickAndPlaceCheezit1已首次正式动作路由验收，原两桌布局、原native顶面接触且无手终态；独立验收另要求实际抓起/连续持物移动/释放。选取XMovePickSim1与boxplace4公开候选，未宣称已有loaded locomotion。BendPickSim2也实际选取新抓持候选，任务收益待测。两者入口预留分别776/6006/5218和766/6122/5337，Astra/xhigh/account2/权限/相机均已核验。


### R019 12:25UTC：CloseDoor首轮审计成功，单列关闭目标

41动作146.60模拟秒、3666帧，完整NT/v1 SHAe5b4b6eadb6061e1fa32f4b9373d794d2d12b2df7af59fe976757dda9439486d。初始1.183240712rad，首次手接触前17.78s角漂移0；最终-.174528786rad，旋转1.357769499rad，真实手接触1350条正力记录。每控制步qpos原生双reward复算完全一致，关门阈值连续1.5s，最低base.678409m、最大倾角19.4355度。native-close-door-exact-frame-v1明确碰撞修复变体，非未修改benchmark/非推开10次增量；终态仍手接触，未验证撤手/锁舌。当前推开10/10，另10任务入口至少1审计成功。新BendPickSim2、MobileCheezit1、XMoveBendPick3持续，全部任务仍未完成。


### R019 六类聚焦 ACK 2026-09-16

SIX-TASK-FOCUS-20260916 ACK：已读最新六类范围及人工反馈全文，AGENTS/现有用户要求文件已引用最新优先级。IKEA/地面搬运暂停由原owner收尾，不由SIMPLE重启；三在途BendPickSim2/MobileCheezit1/XMoveBendPick3均在六类内继续完整推理。历史10门与其它10入口成功仅基线，范围生效前在途与后续新回合分层。Grasp等待既有入口澄清，不默选新机器人或重复木块。3.39RMB唯一校准已确认、结算归API分支；同任务同阶段同因至少3次可比独立真实失败且自主修改仍未解才考虑人工求助，所有失败照常复盘，进展视频无需请求分析。ACK及映射见six-task-focus/supervisor-ack.json。


### R019 六类精确映射更正 ACK 2026-09-16 12:43 UTC

已重读最新范围第4条和原README六项表；此前暂定聚类ACK保留在supervisor-ack-before-exact-mapping.json。BendPick改为BendPickMP、Mobile P&P改为LocomotionPickBetweenTablesTeleop、Grasp确认为TabletopGraspMP，其余XMovePickTeleop/HandoverTeleop/XMoveBendPickTeleop。BendPickTeleop/Sim、MobileCheezit、R018木块仅相关变体/迁移来源，不算精确六项。BendPickSim2/MobileCheezit1完整收尾后不续开，XMoveBendPick3是精确入口的切换在途。未因错误映射新启动任何回合。MP先核查适配，不调用特权规划器/不换手型；不用近似变体补分。暂停两分支已由原owner核实。


### R019 六类实测推进 2026-09-16 12:59 UTC

XMovePick4独立seed4已真实动作/第二账号路由核验，复用v3/H001004，组合810/6158/5333；属于范围生效后新测评，非旧成绩复计。HandoverTeleop1按精确入口新reset，借用框架短共同入口并局部修正为右手抓持→左手承载保持→容器释放的完整语义，组合765/5650/4875；当时首动作尚待核验。V1候选其它映射过期，不整套发布，原候选/当前修复保留。ARCH长度、MEMORY-PRIORITY、相机合同既有真实验证保留，不重复旧补丁。

MobileCheezit1完整65动作240.02秒预算结束，v1及连续视频已审；原027/029/065图像支持先抓起后在改变全身姿态时掉回源桌，完成搬运/放置未发生。相关变体收尾不续开，不算精确两桌入口、不算三次人工求助失败。18秒连续片段及原视频绑定保存。首审脚本因未设置PYTHONPATH导入失败，保留后以项目路径运行通过。

MP原生初始化诊断两入口均存在完整命名关节，但旧Sonic runner不可直接复用：root名pelvis、地面z为负、14臂位置伺服/其余力矩执行器、2ms物理。首导出mj_saveLastXML不适合MjSpec生成模型，错误保留，v2改用spec.to_xml完成。最小坐标变换保持几何/相机刚体关系到2.3e-16m、质量惯量不变，像素光照差均值.44/max5，不冒称逐像素相同。BendMP全转力矩+checkpointPD在4.08s倾角25.14°停止；保留原生臂位置伺服+checkpoint腿PD8s不停止、最大8.63°，25mm腕探针实际约64.6/-14.5/26.2mm，仍有明显误差。只诊断，不计成功；下一限定对照补全模型/状态hash并检查TabletopGraspMP，未发布正式MP入口或改在途控制器。


### R019 SIX-TASK-FIVE-STABLE-V1 ACK 2026-09-16 13:05 UTC

已完整读取用户最新覆盖：各精确任务固定完整候选连续5次独立审计成功，随后预登记10回合冻结测评；旧各1次门槛过期，历史与当前四在途不倒签稳定性。AGENTS及five-stable-ack.json已持久化，当前稳定性全部0/5。冻结包含runtime/允许记忆与检索规则/反馈/资产/控制/相机/模型，并隔离终态skill_update建议；仅改文字不视为隔离完成。现有旧task_skill.py的3训练+5测评规则不适用本协议，不拿它当已实现。准备最小冻结读取与计数边界、非法输入复现测试；在途代码不变。

MP限定对照：Bend两分支原XML SHA c8ddd66e...、完整qpos/qvel/ctrl/外力状态SHA daaf8a3a...一致，额外任务接触均0；native臂伺服保留的8秒站立对照优于全改motor4.08秒安全停止，仅此合同/初态可归因。Grasp默认训练臂姿初始腕桌穿透11.724mm、最大接触1831N；保留原生臂初姿后的相同native状态SHA cd96ca34...，8秒零任务接触、最大倾角3.862°，但25mm探针实际仍后移41.7mm，跟踪动态待核。原任务/桌位不改，无正式MP或新成功信用。


冻结边界最小实现：rsi/frozen_skill.py新增固定公共memory快照读取、哈希完整性、候选隔离建议、不同task/version/reset拒绝、五连胜计数与独立10seed检查。基线真实复现原SkillMemory会改当前skill并读新增总结；首次red log仅模块尚不存在，明确不冒称行为复现。7冻结边界+3现有账本测试通过，非法建议先保存rejected再允许纠正，未破坏完整skill_update。当前尚未接入runner/全配置manifest/完整来源allowlist，任何回合都不标冻结或稳定性。


### R019 13:52UTC：四旧队列收尾、首个低桌成功及冻结准入缺口

XMoveBendPick3完整67动作236.58s，独立审计成功：最终盒底升高88.003mm，原点98.329mm，真实对向指承载且无非手支撑连续10.28s；065独立保持1.2s全部成立。原生8cm阈值、最终站立、原RGB与完整turn/v3均核验。583奖励数值及1采样成功标志差异保留，不冒称逐值重演。v3 SHA97513bfd...。旧队列学习成绩，不倒签五连胜。完整视频与连续末30s短片保存。

Handover1完整47动作140.36s原生success，完整任务审计否决：右手019独立承载约1.48s、给予手清离后的左手043独立保持1.50s成立；047仍左闭合.38、触及容器后原生触发，最终未释放、无目的地独立支撑。末瞬时native_flag=false并不抹去此前记录的trigger；原始result未改。success_review=false和failure_review同时留证。下一reset2仅任务指导强调全盒/沿口余量与受控释放，原生判据/控制未修改；v1及短35s转交至未释放片段保留。

BendPickSim2完整70动作240.76s预算、四次探针/保持无留握，相关变体收尾不续开。XMovePick4完整48动作240.12s预算，双手始终张开，低/向内可达姿态饱和，未包络/闭合/抓起；H001004保持，不把预算截断或不同失败混算同因。二者完整修订与失败审查已保存。

冻结最小接入已加入原runner：公开memory/来源快照、引用改向、固定检索审计标签、终态建议隔离、版本/入口/reset/seed顺序检查、真实host审计绑定及动态账本计数。先前单独memory边界进一步接入；33项针对测试通过。实际XMoveBendPick4选择来源已指向封存副本，入口738/6022/5265；但真实thread/start额外自动加载RSI/AGENTS.md，候选0002未覆盖此源，准入审计明确否决稳定性计分，不倒填哈希、不截断物理。该回合仍完整turn/skill_update后保留物理结果与隔离建议；新源码变更会使旧候选末次完整性校验失败，属于已知配置资格缺口，不补造冻结收据。下一候选003已准备未封存，新增实际instructionSources逐项hash在turn前核验、运行环境包版本及CLI包依赖。候选001仅封存未发模型/无物理，因完善账本在启动前替代；保留所有原manifest。

新独立XMovePick5学习(816/6175/5344，H001004)、精确MobileBetweenTables1学习(733/5638/4896)、Handover2学习(808/6043/5224)、XMoveBendPick4资格验证均已实际动作并核验第二账号Astra/xhigh及workspaceWrite/on-request+auto_review。没有重复旧reset或追加IKEA/地面任务。仍全部0/5稳定性、尚无冻结10回合。

MP原生臂初姿下零/25mm同激活集对照：初态/模型hash匹配，5s前轨迹完全相同；腕x响应瞬态峰值26.1/45.7mm、末差仅1.54/5.60mm，不能仅终点判输入丢失，也不能认为已稳态跟踪。无任务接触/安全停止。追加目标/实测/原生执行器日志完整qpos逐样本与旧对照一致；原生1000/10位置臂伺服肩关节误差约.12–.17rad且快速摆动。raw actuator force超过joint cap不是关节实际超限证据，未记录钳位后qfrc不能混称。已登记最后一个明确对照：保持原生臂初姿，仅比较checkpoint力矩臂控制；原先motor诊断同时用了训练臂初姿，不能直接归因。MP尚未正式放行，诊断均不计成绩。

MP最终匹配对照补充：原生臂初姿完全相同，只有臂位置伺服→checkpoint力矩PD；BendPickMP/TabletopGraspMP均完整8s站立/25mm参考，未停止且无任务接触，实际前移约12.23mm而非先前后移。允许选择这一配置进行最小MP适配，仍不计任务成功；保留余量误差。下一步是原生对象视图/奖励、根帧和录像绑定兼容测试，禁止继续参数漫扫。证据six-task-focus/mp-checkpoint-arm-native-init-review.json。

### R019 / 2026-09-16 14:13 UTC — XMovePick5 audited; central v4 first live load, latest scope ACK

- 已完整读取 SIX_TASK_FOCUS 的中央发布/学习不中断覆盖、BENCHMARK_ALIGNMENT、ISAAC_CONTINUATION_API_AMO 与最新 AGENTS。框架是唯一 skill 作者；本 supervisor 负责执行审计。180 正式回合只是计划，L0/L1/L2/Isaac实际输入尚未对齐；不把旧学习追认为榜单。已授权 API 上限现为60000，沿用负责人共享账本，本线程未查询余额/费率或发新付费调用。
- XMovePick5完整35动作/156.52sim秒、终态推理及v5提案保存；独立审计成功，H001004语义辅助，learning非稳定性。原状态重建reset hash完全匹配，连续承载18.8s，独立保持032与034均4s，最终苹果全底面升高106.02mm。保存中间reward/flag采样差异，不声称逐值复现。证据 episode-0005/success_review.json、six-task-focus/xmovepick5-geometry/result.json，原连续录像156.56s。
- XMovePick6新reset通过中央 v4 完整code/spec/feedback hash门禁后启动：release8bcedb699ddb702c08b751a9d8e134af6c8c938c2560b8fcc018cfefda475073。max_episode_steps=None、提案隔离；是否实际首动作单独验证。其他三在途保持旧已加载代码，无安全预算热调整接口；旧240s限制明确保留至自然边界，不能倒签新profile。
- 两精确 MP backend实际站立/当前物体视图/摄像与原生手几何通过；forcePD保留native初始手臂姿势，世界统一平移不改相对几何。原生object velocity/外力保留，旧诊断清空速度差异已注明。接线/spec暂存 six-task-focus/mp-integration，不覆盖中央caller；中央release ready_for_load尚未放行。后续原生阈值和绑定核验单列。
- 新ACK/MP文件协调已发既有框架辅助executor queue；主owner在第二账号无rollout，此次直接queue失败如实保存，不回退主账号；辅助receipt仅queued，不冒称ACK。未重发旧被拒CloseDoor/IKEA消息。

### R019 / 2026-09-16 14:19 UTC — 180 existing configurations and target mismatch

- 只读本机已有simple-eval精确六项每级10份meta/episodes.jsonl，180份均存在，无下载/无动作parquet读取。benchmark-existing-config-inventory.json保存来源hash、配置hash、因素变化计数；benchmark-180-plan.json只是待对齐计划，不是已执行或最终预注册。
- 实际DR/layout目标：XMovePick=cracker_box0，但保存dr_cfgs仍写apple12；Grasp=chips_can10，默认入口学习为apple12。其余四项都是cracker_box0。不能根据旧声明字段或env_id把苹果学习追认为相同benchmark目标。MP草稿已注明这项依赖，中央发布辅助已queued通知，不冒称已ACK。
- 三个level的材料、光照、空间字段都变化，目录整数不能单独证明官方等级协议；Task.reset原生options.state_dict路径已定位，原生TimeLimit来自评测wrapper/task metadata，50Hz tracker不能直接当该预算单位。Isaac真实策略RGB接入仍待框架，MuJoCo学习继续。
- XMovePick6已实际执行5+动作，第二账号/model/effort/sandbox/auto_review及v4hash均验证；actual入口792/6028、预留794/6048/5239，max_episode_steps=None，不声称已跨旧240秒或终态提案成功。原子提案xmovepick5-public-atom-proposal.json等待中央发布；未改全局skill。
- MP原生语义2tests+双入口subtests通过：29命名force执行器/限幅，单tick20ms与500Hz物理，原生9cm/1.8cm阈值，物体view重绑和named状态恢复。两场景0个actor/0任务成绩。暂存接线未覆盖共享caller。

### R019 / 2026-09-16T14:25:45.889090+00:00 — XMoveBend4 complete; released learning5

XMoveBend4现已完整：62动作240.06sim秒、完整turn、隔离skill_update fab36f283eb76a3139e5b58451f889f5dfbd40727610fcb3abccda2715e278d9，原campaign入口v3未覆盖。56到位超时/6target_reached，全程closure=0，末盒仍桌上；分类旧累计预算截断，未完成阶段为接近/低位可达/张手包络，不是闭合后掉物。final failure_review和原240.08s录像已保存。模型完成后固定依赖校验按预期拒绝代码漂移，result/proposal完整保留；初始ambient-source缺口已单独否决streak，不把该后验校验异常当额度/推理中断。

完整审查后已启动同campaign新reset5（非旧轨迹续接），tmux simple-xmovebendpick-05-central-v4-0916，发布入口central-v4，phaselearning/no累计截止，不加载第4回合未发布提案。先确认首真实动作再报route实际生效。XMovePick6、Handover2、Mobile1仍在途；后三者中Handover2/Mobile1是旧12000步入口，无安全热调预算接口，完整等待不杀。

管理自然交接前：XMoveBendPick5首2动作实际路由通过，reset c432441b-b63b-4151-bd81-39005082f800；入口750/6107，预留752/6127/5355；与XMovePick6同为中央v4/no累计预算。supervisor-state已原子写continue，旧state/handoff归档，当前四环境pid均存活，唯一watcher356018未改；全部完整等待，后续不重开已有环境。

14:31更新/纠正：上条“当前四环境pid均存活”文字晚于实际快照，表述不准确；14:29真实快照已显示XMovePick6退出/result完整，现为三在途。XMovePick6新审计22动作107.48s，A20抬左踝参考无升足却tilt23.02，A21恢复18.26，A22重复tilt25.21越25deg安全线，非累计截止。failure_review与107.52s录像保存；proposal7cb2e1...隔离，中央v4入口hash未变。已queue中央修订，尚未开7；跨240秒仍未实际验证。state/handoff同步已纠正，旧快照保留。

14:34中央v5自然边界交付已消费：SHA012ee9...，MP接线/正式readiness与Handover弱终止学习wrapper已发布，codehash核验通过。新BendPickMP1/GraspMP1以v5默认原生场景新reset启动，两个已loco_start，不计任务成功。使用只读发布task-spec，先审首实际动作；Handover2在途旧代码保持，待其完整终态后3才能验新wrapper。中央v5新增22成功源；XMovePick6安全反例晚于发布，已queued供后续审改，不无修改重开7。

14:39真实MP接入回执：BendPickMP1 resetf4249998...和GraspMP1 resetcb771121...已实际action，account2Astra/xhigh/workspaceWrite/auto_review核验，预留入口752/5784/5023及744/5656/4903。只是正式学习首动作，0成功/非榜单。Handover2完整77动作240.36s、6010帧，公开0037/0077确认移交松手后盒回桌与末重抓未果，原预算截断；failure_review保存，与Handover1弱终止不是同因。Handover3新reset采用v5新完整完成wrapper/发布spec，首动作和跨native弱触发待验；不把两个接口加载称物理收益。

2026-09-16T14:41:12.291233+00:00 自然管理边界：五个在途明确交接，最新state=continue/hand-off已更新，两个MP首动作已验证，Handover3已新reset用v5 wrapper、待首动作及跨native里程碑实测。没有杀模型、重放未知动作或重复主管；唯一watcher保留。全部原目标仍未完成，0/5稳定、0正式测评。


### R019 / 2026-09-16T14:49:59.131057+00:00 — 六项继续 ACK 与 Mobile1完整失败审查

已重读最新全局/六项/人工反馈至末尾/榜单及分工；60000共享预算由原owner维护，不查询。四个当前actor保留、唯一watcher未改。Mobile1完整57动作240.38s、48timeout/9到位；31抬盒、32转向失物，后续空手移动，240.4s/6010帧原录像已保存。完整v1提案8e17bc...，独立failure_review为旧预算截断，不混称无法继续的物理失败/三次同因求助。下一Mobile2使用中央v5新reset和maxNone，未发布提案不加载；不伪续旧回合。AMO独立候选工程交接已读，生产/真实物理仍待中央接线。


### R019 / 2026-09-16T14:59:40.012055+00:00 — MP安全停止、Mobile2首动作与保存配置实测

BendPickMP1完整15动作53.70s触25.215deg倾斜安全线，双手全open、未包络/抓持；failure_review保存，原生failure字段只是host配置终态，不能误称原任务终态失败。原0014/0015 RGB已审，53.72s/1343帧视频可读。提案4d2b51...隔离，published入口37675b...未变；首提案因引用agent/NOTES.md不在rollout证据域被拒，第二次自行纠正。此前中央消息误称超长，已生成更正。

Mobile2真实3动作及第二账号Astra/xhigh路由核验，reset986a86e0...、实际入口749/5802/5044，预留751/5822/5062、中央v5、maxNone。Mobile1原连续28s摘录（视频108–136s）已保存，700帧/原速，无人工必答。原网页已发现Mobile1/BendMP1连续视频。

限定配置核验：XMovePick level0首个保存状态实际编译cracker_box0，而cfg声明apple12；GraspMP实际chips_can10。dr_level=None保留完整spatial，原资产管理器按ID解析旧绝对路径到本地已有资产。两例零policy动作；native reset内部一个tick明确记录，不算attempt/成功。v1访问MP顶层mjModel及v2 numpy报告序列化错误全保留，v3修复报告后通过；不是环境故障，未改在线控制器。source配置不改，正式等级/控制初态/时间单位/Isaac尚待完整对齐。证据saved-config-reset-summary.json。


2026-09-16T15:06:19.272358+00:00 GraspMP1完整27动作97.94s、2449帧97.96s，倾角25.803deg安全停止；全部open，无抓持。公开026/027已审、failure_review和ddcab637...隔离提案保留，原v5入口未改。两MP跨任务负迁移候选存mp-multistep-negative-transfer.json供中央审查，不当3次同因求助，不自行发core。XMovePick7改用现有正式v5新增episode5成功来源，首真实动作/新reset9f3e102c...及账号2路由验证，791/6020/5214；这不是v6安全修复或旧6续接。


### R019 / 2026-09-16T15:12:50.341807+00:00 — XMoveBendPick5真实抓持审计通过，终态高度限制单列

59动作234.44s，完整turn与e214417...隔离提案。原生8cm事件真实出现于059，原点峰值85.98mm，18.38s对向承载/无非手支持，055/057独立保持各2.5s。原0057/0059 RGB及5862帧234.48s视频已审，同seed完整qpos/qvel hash匹配的几何重建不是新attempt。最终仍握持，但原点降至74.35mm、盒底70.89mm，即时native_flag已false；本审计按现有task-spec高度达到+独立安全留握计学习成功，明确terminal_height_threshold_satisfied=false，不冒称8cm终态保持或五连胜。1030奖励及1标志重算采样差异保留。无人工反馈/示教；未跨旧240s。中央收到该限定边界后再决定经验晋升。本task审计学习成功共2，固定候选仍0/5。下一6用已发布v5新reset，episode5未发布提案不加载。


### R019 / 2026-09-16T15:21:54.213529+00:00 — Handover3首个完整学习成功及弱事件连续性实测

53动作185.24s，完整turn/proposal2963c3...；独立success_review通过，原手交接→目标容器释放全部完成。原生事件action50时完整结果仍in_progress，同reset继续51/52/53，额外9.22s真实物理后task_success。右独持026为1.5s、左独持038为3.5s，最终独立容器支持且无机器人接触2.18s/110样本，位移最大0.731mm/旋转0.002418rad。几何重建初态全hash一致，COM/底部顶点在basket足迹内且底部低于最高沿40.89mm，原0051/0053相机图支持下端入容器，最终几何仅basket接触。凸足迹非全体积证明的限制保留；不声称withdraw动作、Isaac或RTC。无人工反馈/示教，原生标准不改，扩展学习wrapper区别于原生榜单。4632帧185.28s完整视频和末40s短片保存。此为首个Handover完整审计成功，稳定性仍0/5；未跨旧240s。

中央前工程turn.completed及无同thread进程已核验，依用户明确授权通过原account2 launcher接续同一01a0a94d，rsi-central-followup-1516；不新建作者/物理调度。优先两MP反例与新成功中央发布，AMO46项离线候选已ACK但还需独立recorder/场景/Isaac/实际动作验收。


### R019 / 2026-09-16T15:33:53.439539+00:00 — 自然管理边界与新Isaac工程回执

五个新增终态review已完成；三后继真实在途接管信息已原子写state=continue并归档旧快照，唯一watcher未改。中央原owner同线程续交正在v6证据审查，不并发resume。Isaac15:24工程回执已读：独立同reset一新动作/两完整APIturn实际Isaac附件+封口视频验证，0任务分；当前三个学习仍MuJoCo，已queued中央发布与原renderer新reset租约协调，queued不等于加载。AMO中央离线候选已ACK，实际物理/独立recorder仍待。账本生成器只纠正MP已接入/旧候选状态文案，不改controller/actor。


### R019 / 2026-09-16T16:17:26.819109+00:00 — 新目标ACK、XMP7完成、MP分离实测与接续准入复核

已读最新CURRENT_EFFECTIVE_CONTRACT及PSI0目标，ACK artifacts/psi0-goal-20260916/simple/ACK.json：完整180>=155是最终门槛，五稳只准入，formal0。XMP7完整独立留握抬升审计成功，辅助学习，视频169.36s及30s连续片段保留；Handover4新v6实际route/入口长度已验。Mobile2同reset跨240s，XMB6也继续过240s。MP A/B完成，Grasp关闭PI降低对臂耦合却加重主腕超调，不晋升；Bend局部小探针不代表完整低位接近。原生保存config下目标/settle两实测通过，首版capture目录故障保留，MP世界平移差已单独校正。native协议README双CLI来源/时间单位及180配置约束落盘。接续release f39ee950收到/hash核对，但四个合成协议红例仍eligible，已ACK不加载并交原owner；旧watch/三个actor继续，无重复模型。全部细节/证据与明确下一步见 ref/ACCOUNT2_LIVE_CONTINUE_20260916.md。

Handover4新增实际连续性证据：45动作处finish_attempt返回rollout_finished=false，随后46–49四个物理动作完成；同reset7679836f...，非仅接口单测。见artifacts/psi0-goal-20260916/simple/handover4-stall-continuation.json。16:17:59最新在途：Mobile2 128动作386.46s、XMB6 74动作282.46s、H4 49动作159.74s，均无result，继续原进程，state=continue；不是complete。


### R019 / 2026-09-16T16:42:32.115237+00:00 — 稀疏模式真实物理对照与现行合同续接

已ACK现行六项/155-of-180合同和既有finish gate修复；未重改旧>=3规则。三个原actor继续，H4实测finish45后续行动并同reset跨240秒。状态writer新增written_ns、下一实际边界、actor PID/start_ticks/boot与终态路径；原watch未改，旧快照/源码备份保留。

本轮新诊断3个独立reset同全qpos/qvel初态hash：UMI-4/Pelvis-1/Mobile-7均8秒站立通过；后两20cm参考实际仅前进43.994/37.141mm，未达10cm准入所以不叠加turn。实际ONNX29目标/命名PD、整脚几何50Hz审计和3段连续8.04/12.04/12.04秒录像齐。所有足底碰撞geom至少一处仍与地面重叠；P1双腕峰值17.46/13.11cm是持物负迁移候选。排除纯UMI mask即充分原因/此次静态前路碰撞，未排除其他动态参考/原生站姿；不声称模型不能行走。REVIEW和中央queue见psi0-goal/simple/sparse-mode-probe-01。下一不扫参，等待原中央AMO root修复后对照；不计任务/人工三次失败门槛。

v7接收和9文件最小hunk写权ACK完成；检测中央已被原owner恢复，guard拒绝重复模型。v8短role metadata预检新通过但发布/物理未准入，不能报加载。API工程公开输入草案仅公共阶段投影，操作审批未绑定、不填虚假approved；四工具合同冲突与回执接口已queued原fallback。完整180正式仍未运行，非complete。


### R019 / 2026-09-16T17:20:31.287979+00:00 — AMO真实离地但站立不准入；真实API操作接线与最新首发顺序

本轮完成独立AMO真实物理诊断，原三回合继续。AMO source最小副本修正自由根检查、最后安全tick记录和约1e-21rad原生finger初值舍入；旧source/旧两次零动作拒绝保留，5项针对测试通过。diagnostic-0003为新独立reset，真实CUDA500ticks/10s，不是actor任务。零导航8s峰漂移1.687m、tilt23.914deg、minroot.619m；左右整脚最大clearance102.58/75.76mm且38/53个50Hz采样>1mm。证实该独立控制下确实离地，不证明UMI能行走或AMO可控搬运。脚本漏5cm/yaw站立准入导致后2s前进/停止执行，已明示protocol_deviation并修复未来准入（真实坏trace+3合成检查通过），未删改旧结果，不再扫参。连续视频10.04s/251frames25fps和geometry审计齐，REVIEW、candidate.patch、原版及测试在simple/amo-root-candidate。

新版goal gate四个旧红例已拒且production拒synthetic，v2/v3接续源码与真实public刷新已核验。通过正常exec工具真实安装3个精确原reset终态核对操作，完整输入/返回chunk8e8548/0a4819/651b45保留，未自填approved；production supervisor-api-tools.json及api-binding-validation/result.json已落地，0付费/模型/物理。权限仅这3终态核对，不等于任意后续launch获准。

中央v8/v8.1集成/发布已接收但API管理依赖又漂移，新actor0/reset0，未绕hash创建空episode。核实中央原完整turn结束/无进程后17:14:38沿原review-run.sh续交同一线程；随后完整读到API_FIRST_DAGGER最新要求，记录该一次辅助账号启动顺序偏差，完整等在途，不再新辅助turn。新合同API-first、同完整候选10审计成功+5连胜后才降学习频率，正式180不变；精确原文hash ACK见API-FIRST-DAGGER-ACK.json。原fallback已确认暂停旧错误首发路由，PAUSE不杀3actor；helper因PAUSE自然退出，故未写watcher_upgrade_boundary/未冒称新listener加载。原owner在实现新API-first顺序和唯一listener恢复，需准确本管理PID3249453/current log绑定，不能复用active-supervisor旧PID292946。

17:18快照：Mobile2 217动作659.94s，XMoveBend6 132动作500.76s，Handover4 108动作329.08s，均原reset、无result、继续完整推理。H001004已按原文hash2aa49674 ACK，实际消费边界是XMP7新reset，不热注入当前。六项五稳0、正式未测；历史door10成功保持不重做。已有视频页公开阶段已刷新，当前MuJoCo并非Isaac/RTC。

## SIMPLE主管自然边界 2026-09-16T17:55:33.816856+00:00

XMoveBendPick6完整结束并通过独立学习审计：142动作、526.96模拟秒；末帧native原点抬升80.728mm，整盒底部比初始升73.364mm，带对向受力指的无桌面支撑连续19.62s，预阈值单独hold138/140分别2s/4s。完整turn与skill proposal齐；原始26,349轨迹样本和527s连续视频保留。保存状态重建仅作审计，非新attempt；数值reward重建1,602项小差异原样记录。不宣称终态额外dwell、持物行走、五稳或正式成绩。XMB学习审计累计3，Handover1；官方cracker目标XMP0，旧apple辅助成功单列。六任务当前冻结候选信用均0，正式未运行。

中央v8.2真实40源码pin准入后启动唯一新BendMP2，初态reset4424f6d9-b615-47f4-bfc0-c9b572827cd8。实际normal exec审批3f9311通过，保留精确26公开输入/工具/指令binding。随后在任何API请求/动作前失败：same_reset_api.check_live把LiveSim.closed（Dex3闭合目标numpy数组）误当closed生命周期bool。原caller已自然cleanup，0API请求、0动作、无skill_update，分类基础设施不计能力失败。无旧reset伪续、无重发、无重复空episode。无物理红复现已保存；隔离候选5测试通过，公共源码未改，原中央已结束，后续queued消息不冒称ACK。中央须经API-first渠道接续发布后才允许独立新Bend3。

训练分配小工具9测试通过，分别记录兼容目标/控制/反馈cohort累计训练成功和当前任务真实依赖候选成绩；基础设施/预算/未封口排除近期能力失败分母，所有原记录保留。当前各项均不具备降频条件，正式180计划不自适应。H001基线完整复现报告已消费，不占物理槽、不加成功或三次失败数；003/004已回答的抓法高度不再提问。

管理API-first v4（08272509…）17源码hash全匹配、6项路由/输出边界独立复验通过；新唯一helper3665862等待本管理turn自然结束及原锁释放。三个原终态操作按v8.2源码实际重新审批（9881a5/e89a70/a23d84），公开动态刷新验证通过；配置只覆盖原终态核对/刷新，不授权任意工程shell/新任务。实际管理API尚未请求，物理API也未请求，不混报切换。Mobile2/Handover4仍原reset活着，后续完整等待，不设墙钟/动作/累计秒截断。

证据：simple/xmovebendpick6-geometry/result.json、R019/xmovebendpick-campaign/episode-0006/success_review.json、simple/bendmp2-closed-red.log、simple/api-lifecycle-candidate/、simple/learning-allocation-current.json、simple/api-binding-validation-v82/result.json、simple/api-first-v4-independent-tests.log。

## SIMPLE-BREADTH-20260917 管理接续 2026-09-17T04:52:01.118460+00:00

本节覆盖以下历史六项/巩固/180调度文字。用户已改为 SIMPLE 简单相似任务一次完整审计成功覆盖；API 停用，仅隔离辅助20x Astra/xhigh，禁止主账号。13个精确任务/学习变体已有审计成功，全部退出新重试队列；不称13/60，当前91注册入口仍须按任务与变体映射。旧正式180/155目标暂缓，未完成。

- 下一任务：`simple/G1WholebodyHandoverSimToRealTeleop-v0`，当前已ACK、预检中、未加载/未启动物理/未成功。复用Handover3右手抓持→接收手独立保持→释放稳放的条件经验；不用原坐标或live历史。
- 原中央01a0a94d确认旧turn已结束且进程不存在后，已通过隔离账号恢复一个最小准入回合；原共享writer不变。现有独立预检助手正准备两个相似入口，主管不重复预检。此工程启动不是物理启动。
- Handover4原reset仍保留，PID2804371/start_ticks2379479；已有用户停止文件由原UI协调方写入，等待原推理/执行边界消费，不重发请求或重置。最新公开状态以episode/public-progress.json为准。
- Mobile2已经完整终止：615动作、2149.78模拟秒、失稳停止、skill_update完成，未成功；不再沿用历史“running”。该困难任务暂缓。
- 推门历史完整审计10次保留；[最新完整连续视频](http://127.0.0.1:8765/media/simple-door-episode-0020-1789557962243404040.mp4)。[Handover3连续视频](handover-campaign/episode-0003/video/episode.mp4)为可复用成功来源，非新结果。
- Psi/AMO用户所指成功配置待精确来源核实；旧失败候选不等同该方案。本主管不为控制研究延迟简单任务。
- 当前唯一主管tmux `simple-breadth-supervisor-0917`沿用原watch.lock；不新建watcher、不改网页写域。细分状态见 `simple-breadth-20260917/supervisor-status.json`。


Handover4状态更正 2026-09-17T04:52:58.509287+00:00: 外部协调方user_stop已确认，host进程不存在，视频2104.56s/52614帧可解析；无result/完整终态，不补造。证据 artifacts/R019/simple-breadth-20260917/handover4-boundary-recheck.json。

## SIMPLE-BREADTH-20260917 实际新回合 2026-09-17T05:09:44.464754+00:00

最新策略：简单相似任务一次完整审计成功即退出。13个精确任务或历史学习变体已有成功并退休；不是13/60正式成绩。困难任务暂缓，5～10次巩固与180正式测评暂停且未完成。API停用，禁止主账号。

- **正在执行**：HandoverSimToReal `episode-0001`，tmux `simple-handover-sim-01-0917`。新reset `bb1bc3f1-c8db-4d85-b34b-c925cb437da9`；host PID4006012/start_ticks7174140；第二账号run.sh app-server实际返回Astra/xhigh、workspaceWrite、on-request/auto_review。
- **实际物理**：已完成4个动作，累计16.20模拟秒。第1动作抬手到位，误差8.74mm；随后姿态跟踪超时、无安全停止，actor继续自主修正。动作级超时不是整回合失败；完整交接尚未证明，新增成功0。
- **加载**：中央v8.8 SHA `562e7687b8e5734423e54ee77b0c1cfd8840587b5fffab8f22f7d16e8487c3e1`；完整组合719 words/5873 chars/5145非空白；技能SHA `3a0e2fbeb18f018b0a61a18d9afc8aec7e7274047d1a342b6d2205a0b723646a`。23项回归、两任务真实runner准入通过；构造器任务ID遗漏在启动前已修正。
- **图像/视频**：MuJoCo当前RGB，物理在推理时暂停，非Isaac/非RTC。新连续录像 `handover-sim-campaign/episode-0001/video/episode.mp4` 正在记录，尚未封口，不冒称完整可播放。[历史Handover3连续视频](handover-campaign/episode-0003/video/episode.mp4)为复用成功来源。[推门最新完整连续视频](http://127.0.0.1:8765/media/simple-door-episode-0020-1789557962243404040.mp4)，历史审计成功10次。
- **下一项就绪**：HandoverPlaceBackSimToReal，未启动。第一项是giver释放后左手独立持稳；第二项另需放回原桌并双手释放稳放。两者均无篮筐，不套用旧basket结束条件。
- Handover4由外部协调方按新策略停止，本主管未杀进程或重发。PID已退出，连续视频2104.56秒可解析；无完整result/turn终态，单列用户停止/未完成，不补造skill_update/成功。Mobile2已完整结束：615动作2149.78秒，失稳停止，未成功并暂缓。
- Psi/AMO所指成功配置待精确来源核实，未使用旧失败候选冒充，不阻塞SIMPLE新任务。本主管不修改网页写域。



## R019 2026-09-17 原主管新管理回合：HandoverSim独立审计与并行接管

- 原watch.lock由当前一次性wrapper PID123794持有，原主管01a0a867持续执行；无新watcher。最新版简单相似一次成功覆盖及辅助账号双环境并行已ACK，API/main禁止。
- HandoverSimToReal ep1独立审计通过：28动作、79.24模拟秒、唯一reset bb1bc3f1-c8db-4d85-b34b-c925cb437da9；完整Codex终态和skill proposal；原视频1982帧/79.28秒全解码。3963保存状态仅mj_forward重建、mj_step禁用，无新增reset。右手独立持物28.36秒，末段右手完全脱离、左手独立承载3.92秒，终态盒底高于桌面78.9mm。success_review及哈希已保存，该精确任务退休。当前14个任务/学习变体、27个历史审计成功，不是14/60正式成绩。
- 控制归因发现原轨迹已有腕PI非零项，最大7.5Nm；按完整原发布/实际轨迹记录，不声称纯PD，不安装/应用旧待批准PI包。
- 本地v8.8 PlaceBack启动在任何intent/reset前被源码哈希漂移拒绝，证据placeback-preflight-hash-failure.json。随后原root发布v8.9.1并启动PlaceBack ep1，原主管接管：PID167547/start_ticks7564572/reset de0d11dd-3820-4370-9d99-ce84922e47f9，实际account2 Astra/xhigh和首动作已记录。未重复启动。
- 中央v8.10 BendHandover准入已消费并精确hash ACK；root启动实际输出bendhandover-campaign（不是中央建议但未使用的bend-handover-campaign），PID208077/start_ticks7600813/reset a9188813-eb8c-4dd0-82b3-9655425a46e7。完整组合746 words/6108 chars/5354非空白，首动作已核验。两路当前均未封口、未加成功，等待完整推理与复盘再审计。
- 成功条件化原子单次queue给原中央，回执成功排队，尚不等于ACK或发布；public提案没有host对象/接触真值或世界坐标。
- 抱容器候选源码另含跨桌抱持行走，不作为简单静止交接任务贸然准入。候选只读筛选，无模型/reset/任务分母。
- 原始结果/录像不改，公共campaign_audit和task-evaluation-status按原始来源重建，PROGRESS及本轮supervisor-status更新；未修改human-feedback网页写域。

证据：artifacts/R019/simple-breadth-status-20260917/；artifacts/R019/handover-sim-campaign/episode-0001/success_review.json；artifacts/R019/simple-parallel-coverage-20260917/SUPERVISOR-CENTRAL-CONSUMPTION.json。


### BendHandover1 完整终态审计（本管理回合内）

26动作/115.72模拟秒后，原25°躯干倾斜安全线在25.092283°触发 diagnostic_stability_stop，终态高度0.759m；完整turn/completed、skill_update和2894帧/115.76s视频已封口。独立重建5787状态无物理步进：右/左独立抓持跨度均0，盒子仍支撑于原桌、未接触目标容器。非额度/时限/3动作提前退出；8次finish_attempt均返回继续，实际同reset到26动作。失败归档canonical failure_review/success_review(false)，不放宽安全线。无已验证低成本修正，按简单覆盖先暂缓第二次；候选skill SHA73a41b72d597c282c5db68dfc71d48684d670278397858729c5886e759d882f0仍未发布。新失败和暂缓提案已单次queue中央，ROOT文件交接已保存。PlaceBack1仍在途，主管继续本管理回合等待封口并审计。


## 2026-09-17 2026-09-17T07:25:58.512959+00:00 — BendHandover2 v8.11完成审查

6动作/22.86模拟秒后progress_actor_stall；完整turn/skill_update与572帧录像封口。1144保存状态独立几何复核未见右手独立抓持、左手承载或容器释放。最大倾角11.774°、最低高度.7851m；属于未完成主动停滞，不能记物理失败。HandoverSim1成功原子及空手调姿反例确已选用；新版simulator_supervised_progress_learning单列，不与旧回合合并作因果结论。唯一授权修正复试已消费，暂缓第三次。证据：artifacts/R019/bendhandover-campaign/episode-0002/failure_review.json。PlaceBack1仍原reset持续执行，不热改。


## 2026-09-17 — Variant1原生AMO准入与真实模型接通

原中央01a0a94d两轮工程均通过完整turn/exit0后接续。首次原生预检0控制tick因录像初帧目标字段缺失终止；7项局部红绿后修复，原证据保留。唯一preflight02在独立reset9427f12e-c095-486b-81a7-77bbba586ab1完成10s/500tick，8s站立最大漂移17.04mm、上抬10mm实测7.466mm；没有完整抓取或新成功。独立保存状态几何审查501唯一状态，原502行首态重复不加时长，苹果仍桌面支持。

v8.12发布sha6a65dbfcb98f75b5c6acdb4068f40d337f7639587191604e75e188b9cb4547cc，69源码/311公开/61原生依赖hash匹配。17实际输入文件，组合714words/5723chars/5001非空白。首个Variant1MP学习回合独立新启动，真实thread/start ACK 01a0ae7d-6d22-7ad3-9e06-e0a97efb129f，account2 Astra/xhigh/workspaceWrite/auto_review；API与主账号停用。尚未以启动计成功，继续等首动作及完整终态。PlaceBack原回合保持活跃，不热改。证据：simple-breadth-status-20260917/v8.12-consumption-ACK.json。


### 2026-09-17 Native Variant1 v8.12 实际首轮封口审计
隔离辅助20x Astra/xhigh实际执行8动作、12.52模拟秒（初始化9秒另计）。前7步到位，第8步25mm上抬超时，苹果落地并整体退离桌边。1077独立保存状态+21.56秒/539帧完整视频审计，无对向单手离支撑保持。完整turn及隔离skill proposal已保存；分类incomplete_voluntary_stall、动作级抓取失败，非成功/跌倒/预算截断。调用与RGB绑定已验，原生AMO15+手臂IK实际运行，不代表全成功Psi/AMO方案。证据`artifacts/R019/tabletop-grasp-variant1-native-amo-campaign/episode-0001/failure_review.json`；中央候选回执`artifacts/R019/simple-breadth-status-20260917/variant1-central-outcome-handoff.json`。PlaceBack原reset继续，不热改。


### 2026-09-17 v8.13最后一次Variant1修正尝试实际加载
原中央完整turn/exit0后，审核并消费`central-variant1-outcome/HANDOFF.md`。69源码/315公开文件/61原生资产hash匹配，运行代码及其他任务条目不变；修正闭合后拇指对向及整手支持面不确定度判据，不声称缩短lift已解决退移。一次性launcher启动episode0002，reset `7cba9457-ca6e-4880-adc6-9fd150978b91`，PID1079184/start_ticks8625589，初态qpos/qvel hash与ep1一致但独立reset。实际隔离20x Astra/xhigh应答及757 words/6076 chars/5311非空白已验，组合hash `69c0694bbac358d7f6e5f0c11dc44a3fb376bfa78a9d875ec537df71e4d0fd4e`；此处只记加载，物理/成功另审。PlaceBack原回合继续。


### 2026-09-17 Variant1 episode0002完整封口与暂缓
3动作、7.60任务模拟秒，完整turn/skill_update。v8.13从首次接近启用腕姿保持，前2段2.14/2.90mm残差；25mm下降只实现6.17mm，20.28mm残差、IK未收敛，未建立包络，actor主动延期。831独立保存状态与416帧/16.64秒全视频审查：苹果一直桌面支撑，无手接触、闭合、抓持或抬升。原reset独立且初态hash与ep1相同；不把主动未完成写安全/物理失败或成功。两次机会耗尽，暂缓，不开第三次/换同机制变体。审计`artifacts/R019/tabletop-grasp-variant1-native-amo-campaign/episode-0002/failure_review.json`；原中央公开回执`artifacts/R019/simple-breadth-status-20260917/variant1-episode2-central-outcome.json`。PlaceBack1继续原冻结回合。


### 2026-09-17 PlaceBack在途前缀独立审查，不是终态
仅复制原reset至action183的不可变保存状态前缀，38134状态；make_simple_env只编译保存布局，mj_step被禁止，无新reset/策略调用/成绩。右/左独立持物区间均0，183末仍桌面支撑且手已脱离；不能将局部可见底边抬高或未持物的table_release几何布尔当作完整任务。审计`artifacts/R019/simple-breadth-status-20260917/placeback-action183-prefix-review.json`。原actor随后继续至191动作，新一次闭合中；不截断、不热改、不喂host真值，后续仍需完整终态审查。


### 2026-09-17 PlaceBack1用户停止的完整证据审查与归因更正
192个唯一闭环动作、791.42任务模拟秒；195次动作工具调用中的3次在执行前被校验拒绝，全部回执可核，没有未知物理重发。39,572保存状态独立几何审查无右/左独立持物跨度，最终仍桌面支持；原视频19,786帧/791.44s完整解码。没有turn/completed或skill_update，原始result/log/video保持。初见EOF曾暂归基础设施中断；随后消费root的user_stop.json、停止进程证据与最新COVERAGE_CORRECTION，现正确分类为user_requested_stagnation_stop / user_stopped_incomplete，不计物理失败或成功，旧判断版本保存在before。原主管未发终止，但root明确按用户要求结束该长链。
最高优先级Mobile原盒子抓起前不能转身搬运的网页反馈已精确hash ACK，未追认旧回合使用。当前原中央正在完成候选，root准备Variant3MP/近容器PickNPlaceVariant1MP两路；预检不是物理actor成功，不重复启动中央/actor。证据：simple-breadth-status-20260917/coverage-correction-ACK.json、handover-place-back-sim-campaign/episode-0001/user_stop_review.json。
