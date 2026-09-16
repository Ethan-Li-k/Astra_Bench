# M0 预检 — 2026-09-14

状态：接口审计和局部适配完成；5 项回归及两个短时运动探针完成。完整 M1 仍未验收，未开展抓取；最新结果见 ITERATIONS.md 的 R001。

## 当前最小路线

选择已有本地 MuJoCo 依赖作为后续候选，优先利用 locomanip 的机器人资产、具名映射和观测构造，在 RSI 中建立明确针对 model_38000 的边界。此次未验证场景加载、相机、稳定站立、手指接触和取消能力，所以候选不等于已可运行。

暂不把 Isaac 场景迁移、完整房间、人类视频重建、外部多 agent 框架作为前置。首个能力实验为自由站立的单手方块。

## 实际读取的资产与入口

- checkpoint：`/home/galbot/Downloads/model_38000.onnx`，16,568,306 bytes；SHA256 `d87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa`。
- 配套说明：`/home/galbot/Downloads/fsq_scaletrack_vla_interface.md`，§2.1 关节序；§3.1 task 编码、完整 anchor、时序；§3.2 mode；§7 旋转约定。
- 原始 PT：`/home/galbot/Downloads/model_38000.pt`，66,812,193 bytes；此次只确认文件，不反序列化。
- 候选代码：`/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/bfm/scaletrack.py`。
- FSQ raw 路径：同目录 `scaletrack_raw.py`，FSQ 类继承基类坐标分支。不要与另一个显式 full-anchor 的非 FSQ 类混淆。
- 历史镜像：`/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/scalebfm/tracker.py` 及 `runtime_mirror/runtime/model_38000_metadata.json`。镜像 wrapper 是另一套 scripted 调用契约；mode_index 映射等尚未核清，不直接拼接到原始 ONNX 路径。
- 可用依赖解释器：`/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python`。此次只读导入 numpy、mujoco、onnxruntime、scipy；不改环境。未安装 onnx 包，无需为签名读取安装它。
- 旧回放入口：`/home/galbot/lizekai/Loco_manip/locomanip/scripts/play_motion_track.py`；仅参考，不直接启动。

## 实际 ONNX 签名

- `policy`: float32 [batch,3,64]
- `policy_task`: float32 [batch,6,253]
- `action`: float32 [batch,3,29]
- `mode`: float32 [batch,14]
- `mode_mapping`: float32 [batch,253]
- 输出 `actions`: float32 [batch,29]

签名读取只创建 CPU session，没有执行网络推理。动作反归一化、PD 与历史处理仍须按实际适配路径核验，不能仅凭输出名字认为是关节角。

## 接口缺口与具体证据

1. `scaletrack.py:923`：`_full_anchor_quat = "pelvis" not in mode_links`；`1071–1075` 决定 full/yaw-only。VR-5 包含 pelvis，因此会进入 yaw-only。已执行构造输入复现，详见 ITERATIONS.md 的 R000。
2. `scaletrack.py:912`：未知 mode 回退 Head-Hands-3。RSI 边界应拒绝未知 mode，不允许拼写错误静默改变控制模式。
3. `play_motion_track.py:94`：默认 UMI-4；`132`：hand_comp 默认开启；`1458` 附近实际计算额外关节力矩。`utils/hand_force_comp.py` 明确使用 Jacobian 转置生成额外手臂力矩。这是额外控制成分，需要从本项目主基线排除，若未来研究则另开对照。
4. `scaletrack.py` 未来 offset 默认末项 25；镜像 tracker 是 33。两者都可能在文档范围内，尚未验证实时 reference buffer 是否提供对应时刻数据。不得无依据统一成固定数值。
5. R000 时 RSI 没有运行代码；R001 已新增独立适配、测试和短时诊断。`move_tcp()`、在线 observe 和取消等仍未实现，不应将诊断脚本称为完整 harness。

R001 补充：Downloads/model_38000.pt 与镜像原始 PT 的 SHA256 完全相同；在此基础上采用镜像 sidecar 具名动作 scale，明确采用其源 g1_29dof.py 的 PD 参数。局部适配实现于 RSI，不修改其他项目的通用默认。旧 scripted 转换代码将 mode 固化为全 14 点；当前实验使用原始 ONNX 显式 VR-5。

## 套餐内 Astra 的使用方案

本地 `codex login status` 已返回 ChatGPT 登录，未读取凭证文件；`codex exec --help` 已确认 image、model、output-schema、json 等参数存在。没有为核查发起模型推理。

官方说明区分 ChatGPT subscription access 与 API usage-based access：
https://learn.chatgpt.com/docs/auth

非交互执行与结构化输出说明：
https://learn.chatgpt.com/docs/non-interactive-mode

优先由当前 Codex 会话进行开发分析和必要图像审查。真正评测 actor 必须另行限制可见输入；当前审查会话已读配置和开发证据，不能直接充当严格 P0 测试 actor。

后续若需要自动视觉动作决策，可验证 ChatGPT 登录下的 `codex exec`、显式 gpt-6-astra、图像输入与结构化动作输出。不是每个底层控制 tick 启动一个 Codex；本地控制必须独立运行。模型是否可用于该 CLI 调用、权限隔离是否充分、延迟是否可接受尚未实测，不凭登录状态宣布端到端可用。

只读 sandbox 并不自动阻止读取工作区中的物体真值、API 配置或评测文件。actor 隔离必须有实际权限边界，不能只靠“不要读”的提示。开发日志与 evaluator 不进入 actor 可读目录。

禁止以套餐不可用为由自动切换 api.json。无需重复颜色识别等已完成的 API 测试。

## 已检索框架如何复用

本节复用此前已读源码/论文的结论，不声称已安装、移植或验证成功。上游代码正式引入时才固定 commit 和许可；现阶段不为收集目录而克隆全库。

- **Show-Harness**：优先复用动作词表、机器人解释器边界、近期实际动作反馈。原 `core/action_units.py` 给出有限方向、旋转、开合 token。换为本平台参考生成器，原步长/机位/夹爪判据不能照搬。源码 https://github.com/showlab/Show-Harness/blob/main/core/action_units.py ；论文 https://arxiv.org/abs/2609.10522 。此前配置核查为 Gemini-3.1-Pro / GPT-5.5 分支，并非本平台 Astra 结果。
- **PIVOT**：用于候选动作的视觉表达和选择；是方法借鉴，不声称已有可直接部署的完整仓库。https://pivot-prompt.github.io/ ，https://arxiv.org/abs/2402.07872 。此前核查原模型 GPT-4V，并研究 Gemini。
- **KAT**：借鉴观测—动作配对示范及 token 化；先保留真实执行增量和图像结果，不先复刻全部关键点系统。RSS 2024 / GPT-4 Turbo：https://www.roboticsproceedings.org/rss20/p096.html 。不是单人视频直接生成当前人形动作的证明。
- **Inspect Robots**：候选运行时与日志组织参考 https://github.com/robocurve/inspect-robots 。套餐 CLI 后端、观测权限和人形 adapter 都需另行核验；不能假设其默认模型入口走套餐。此次不作为强依赖。
- **RoboRSI / ASPIRE**：现在复用失败定位、单变量修订、验证后固化的机制；不部署多角色在线链或照搬原始感知/物理辅助。https://github.com/nssmd/RoboRSI ，https://github.com/NVlabs/ASPIRE ，https://arxiv.org/abs/2607.00272 。外部框架不能直接补足本项目 tracker 接口。
- **HumanPlus / S1**：用于后续任务示范与跨视角关系，不进入本轮接口修复。S1 的示范能力依赖其机器人预训练，不能推断通用 GPT 已有相同动作能力。

## R001 可验收目标

保持检查范围小：model_38000 专用适配正确处理 VR-5、完整 pelvis 旋转、具名关节序、合法模式、真实时序和动作历史；先跑秒级数值回归，再做有时间上限的基础运动。

基础运动的记录必须包含请求参考、实际腕部/骨盆/脚部状态、时间戳、取消事件及 RGB；不使用物体真值作为 actor 输入。站立/单腕/手指都通过后才进入物理抓取可行性检查和 GPT 动作表达比较。具体运动范围由当前机器人证据决定，未核定前不写成无限或随意的大默认。

同一故障若两次检查仍无新增证据，暂停该分支并提交缺失证据；不要反复跑完整抓取。每轮更新 ITERATIONS.md。
