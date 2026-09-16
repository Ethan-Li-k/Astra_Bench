# ROBOT-STABILITY-OBS-V1：有限候选交付

**candidate_only，未部署，未改在线源码、控制器、安全阈值、技能或在途回合。** 两文件仅新增77行：命名 pelvis 的世界高度、wxyz 姿态和与原倾角判据同源的测量；既有 motion trace 增加相同采样及单动作内变化摘要。

高度是命名 body 原点，原高度判据仍读 `qpos[2]`，两者不能无条件等同，因此没有发布 margin。缺失/非有限数据不补零，时间回退或跨身份不计算趋势。host-only 问题证据没有进入 actor 包；不新增物体、接触、奖励或审计真值。

- [补丁](robot-stability.patch)、[候选 live.py](candidate/rsi/live.py)、[候选 policy_harness.py](candidate/rsi/policy_harness.py)、[集成与限制](INTEGRATION.md)。
- [红灯](evidence/red-confirmed.log)：原 observe 缺 root、原 motion 丢 root，2项预期失败。初版 fixture 的依赖错误原日志也保留，未当作独立产品缺陷。
- [回归](evidence/checks.log)：20/20通过（11针对、9现有假后端 harness）。验证命名物体在前的映射、非恒等姿态、精确倾角公式、首样本/reset/缺失/非有限值、递归字段与 poison 隔离、实际 caller 文件输出和原普通观测/运动路径。没有运行物理、模型或 API；测试样本不是机器人真实轨迹。
- [结构检查](evidence/structural-checks.json)：LiveSim 除 observe 外原方法不变，保护、控制器及动作限制未动。原物理 test_live 套件未执行。
- [源快照/hash](source-hashes.json)、[最终漂移检查](evidence/source-drift.json)、[只读 patch dry-run](evidence/patch-dry-run.log)、[交接回执](delivery-receipt.json)。

第二账号 launcher 固定 openai / gpt-6-astra / xhigh，设置证据为本目录原 run.sh。候选只交接唯一 SIMPLE publisher，在自然边界审阅逐 hunk 集成；排队、ACK、集成与物理验证分别记录于 result.json。未向 API/IKEA/桌面主账号发消息，没有扩入排队中的其他请求。

机器人本体可见性改善不证明防止失败或泛化。没有共享 core 晋升，本有界工程 turn 到交付即结束。

交接已于 2026-09-16 11:43:31 UTC 经第二账号 queue 排队一次，消息 `01a0aa07-7a75-79b1-809b-d99c18daa4ca`；尚无 ACK、集成或物理验证。交付文件哈希见 [artifact-hashes.json](artifact-hashes.json)。
