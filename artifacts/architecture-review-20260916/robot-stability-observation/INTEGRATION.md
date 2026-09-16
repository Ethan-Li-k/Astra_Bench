# ROBOT-STABILITY-OBS-V1：候选，未部署

唯一发布者：SIMPLE 辅助 supervisor `01a0a867-d7aa-71f2-8547-e264d6d09ede`。只在自然回合边界逐 hunk 合入 [robot-stability.patch](robot-stability.patch)，不要整文件覆盖在线源码。完整副本仅供审阅。API/IKEA 的入口和模型须自行验证，不能盲用本补丁。

## 已确认的语义

- 当前 [LiveSim.tick](snapshots/rsi/live.py:465) 用 `adapter.body_ids[0]` 的 `xmat.reshape(3,3)[2,2]`，经 clip/arccos/rad2deg 得到倾角；该量是 **pelvis 局部 +Z 与世界 +Z 的夹角，单位度**，不是 pitch 单轴、欧拉角之和或质心倾角。阈值仍是原有 `tilt > 25`；本补丁不改 `tick`。
- [Model38000](snapshots/rsi/scalebfm.py:33) 验证 metadata 的 body 顺序与 `BODY_NAMES` 相同；上游 [scaletrack.py:21](/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/bfm/scaletrack.py:21) 首项是 pelvis，[861行](/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/bfm/scaletrack.py:861)按名字查 body id。
- 新 [root 观测](candidate/rsi/live.py:150) 再按 `model.body('pelvis')` 查找，并确认与上述安全 body 相同、父 body 是 world。高度取 `data.xpos[body_id,2]`：**body 原点世界 Z，米**。姿态为现有 MuJoCo `xquat` 的 **wxyz，body→world**，与原四点位姿使用同一约定。不是 `xipos` 惯性中心、subtree COM 或第一个自由关节。
- 高度安全门槛仍使用原有 **`data.qpos[2] < .55`**。只在机器人 freejoint 为 qpos 起始关节且对应 world 下 pelvis 时，它才与此命名 body 高度等价。本地 [G1 XML:154–158](/home/galbot/lizekai/Loco_manip/locomanip/assets/unitree_g1_5010/g1_mjx_track_dex3.xml:154)有 world 下 pelvis / `floating_base_joint`；这不证明所有 SIMPLE 组合模型的全局关节地址相同。本轮不构建/加载物理环境，因此**不补造远端运行时地址验证**。补丁在物体 freejoint 排在前面时仍只读命名 pelvis，不把物体高度当本体反馈；也不修复既有控制/高度判据的根关节顺序假设。
- 因上述差别，**本次不发布阈值或 margin 字段**。不把命名高度重定义为安全状态，不给“尚安全”“可继续”的推断。

## 实际接线与公开边界

`SimpleLiveSim` 继承 `LiveSim.observe`，无需新 caller。`LocalFourPointHarness._capture` 将新字段严格重建后保存到现有 observation 文件，附 `episode_id = output_dir.resolve()`。这是本地 rollout 目录身份，不冒称独立 reset UUID；独立 reset 的原审计继续不变。

`robot_root` 只允许五个字段：`body_name='pelvis'`、`frame='world'`、`height_world_m`、`quaternion_wxyz`、`tilt_deg`。缺命名 body、映射不匹配、非有限值或非单位四元数时为 null，不补零。原始 sim_s / observation_id 保留。观察入口和 motion 入口都重新构造该小字段集合，不展开任意 backend 字典。此改动不是对所有已有 backend 顶层字段的新通用清洗器；可信边界仍为当前 robot-only `LiveSim.observe`。

现有连续 chunk 的 `capture_robot` 每次真实 `backend.observe()` 后，将 root、sim_s、observation_id、episode_id 写进同一个 `robot_motion_*.jsonl`。现有非连续单 waypoint 路径仍只记录边界 observation，不凭空增加物理采样或 trace。`robot_root_summary` 只从该动作已经写入的样本计算首末高度/倾角变化、采样最低高度/最大倾角；非预测，不保证两采样间极值。样本不足时 `insufficient_samples`；任一缺值、非有限 sim_s、时间重复/回退或身份不一致时 `unavailable`，无差分数值。函数不缓存上个动作/回合。现有 LiveSim 不支持本对象内 reset，外部时间改动仍由原 `tick` 停止；新 reset 必须新 backend/harness/输出目录，不能靠同一目录冒充连续执行。

host-only 问题文件只用于工程定位，未进入 candidate/actor 包。补丁不读取 object/contact/reward/evaluator/host audit，也不把其结论改写成视觉事实。原 native_outcome、host 审计、检索与 human feedback tier 全部保留，不新增或重标成功标准。没有 skill/runtime 文本修改，无需压缩或截断；831 words /6250 chars /5357 非空白的现有静态入口检查原样继续，本轮不冒称重测了所有任务入口。

## 发布顺序与验收

1. 自然边界，归档当前版本和 [源哈希](source-hashes.json)。重新做源漂移检查；有并发改动时只重基本补丁并重跑相关测试。不得用本候选回退 NT、权限合同、长度、审计检索或 render-frustum。
2. 在最新源码副本运行 dry-run 和离线测试。当前 [dry-run](evidence/patch-dry-run.log)检查两文件通过；[测试](evidence/test-receipt.json)20项通过，含11项新针对测试和9项原 harness 测试。测试直接调用候选 `LiveSim.observe`（只用 `__new__` 与命名数据假件）及真实 harness 调用/落盘；没有创建 MjModel、环境或 ONNX，会阻断误调构造器/物理步进。`test_live.py`的 setUpClass 会初始化模型/物理，因此未运行该整个套件。原 LiveSim 除 observe 外全部原有方法 AST 不变，见[结构检查](evidence/structural-checks.json)。
3. 发布者在下次**本来已授权**的新回合开始时，使用已构建模型只读确认 pelvis/安全 body 相同、world parent、root joint 名称、类型和 qpos 地址；保存 host 工程记录。若 qpos2 非 robot root，明确单列既有高度判据差异，不在本补丁里悄改它。未知映射不共享兼容性结论。
4. 下一新回合固定控制器、reset 设置、动作/物理预算、任务合同与人工反馈层，pin 源哈希。核对首个 observation、一次原有连续动作的 trace 与摘要：同样本倾角与原安全计算相同，时间/身份连续，首次不跨回合差分，公开包无隐藏字段；不插入额外动作，不改阈值。保存原有视频/失败和审计。缺 root/null 不推断安全。
5. 若后续要比较任务效果，只能用另外授权的固定条件新回合 A/B，并报告分母/失败/视频与混杂。本轮只交付可见性，不声称防止失稳、提升成功或泛化，不晋升 shared core。

参考首先复用既有 REVIEW.md 的短 skill/控制合同分离结论，并核对 [GPT-as-Policy EEF 合同:9–24](/home/galbot/lizekai/RSI/ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md:9)：测得状态与目标分开、单位/坐标明确、ACK 后看测量。本次没有搬用 ARX-X5 的关节、夹爪、EEF 数值，也没有扩入 RoboRSI 或其他任务研究。参考和 host 来源 hash 见 [reference-hashes.json](evidence/reference-hashes.json)。
