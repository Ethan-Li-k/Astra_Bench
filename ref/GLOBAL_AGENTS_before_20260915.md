## 每次决策前，先写三行（否则不下指令）

1. **当前问题**：这一步具体要解决什么。
2. **总目标**：它如何服务于最终目标。
3. **不可重犯的错误**：本任务里已踩过、这次必须规避的坑。

## 省额度硬规则

- **我只读取/审查/下指令。**
- **不做没要求的事**：不加投机功能、不加单次使用的抽象、不加不可能场景的错误处理、不顺手重构无关代码。
- **不重复探索**：已知的结论/路径直接用，不再重新搜索确认。
- **能简则简**：200 行能压到 50 行就压。senior 会觉得过度设计的，就砍。

## 环境与存储硬约束（下指令/审批必须遵守）

- **可以新建环境**，但**绝不破坏**：conda 的 `psi_deploy`、uv 的 `.venv-psi`。
- 新环境用独立名字/路径，不覆盖、不改上述两个环境的包与配置。
- **大文件落盘到 `/home/galbot/lizekai/data`**：>500M 的文件、ckpt、权重等一律放 `/home/galbot/lizekai/data`，不写入 `/root`。

## 卡住就停，立即问我

- 需求不清、有多种解读、或有风险 → **停下，命名困惑点，问我**，不要静默替我选。
- 有更简单的做法 → 先说出来。该反对时反对。

## 验收驱动

把任务转成可验证目标再交给：

- “加校验” → “先写非法输入的测试，再让它通过”
- “修 bug” → “先写复现测试，再修到通过”
- “重构 X” → “改前改后测试都要通过”

<!-- BEGIN TMUX_LONG_TASK_POLICY (managed block, edit via installer only) -->
# 长任务一律用 tmux（防断线、防会话终止）

- 任何预计超过 60 秒的命令（训练、评测、大文件下载、数据处理、cache 构建），不要在前台裸跑，
  也不要只靠 `nohup ... &` 或 `setsid nohup ... &`：在 PAI DSW 容器里已实测这种起法会随
  ssh 断开而静默死亡（进程消失、日志 0 字节、无任何报错）。
- 标准起法：
  `tmux new-session -d -s <任务名> '<命令> 2>&1 | tee -a <日志文件>'`
  任务名用短横线风格并含日期，例如 `cache-full-0813`；日志一律 tee 到文件。
- 查看状态：`tmux ls`；查进度直接读 tee 出来的日志文件。agent（无 tty）不要 attach，
  需要向会话内发指令用 `tmux send-keys -t <任务名> '<命令>' Enter`。
- 人工接管：`tmux attach -t <任务名>`（detach 用 Ctrl-b d）。确认任务完成并留存日志后，
  才 `tmux kill-session -t <任务名>`。
- tmux 不可用时的兜底：`setsid --fork <命令> </dev/null > <日志> 2>&1`，
  启动后等 5 秒用 `pgrep -f` 验证进程仍然存活、日志在增长，二者缺一都视为启动失败。
- 经由 ssh 在远端跑长任务同理：先在远端机器上起 tmux 再断开连接，
  任务的生命周期绝不允许依附于任何一条 ssh 连接或对话会话。
<!-- END TMUX_LONG_TASK_POLICY -->

<!-- BEGIN WEIGHTS_DELETE_SAFETY (managed block, edit via installer only) -->
# 删除权重/数据前必须校验第二份副本(不能用类别标签替代)

- 适用对象:任何 checkpoint、模型权重(`*.safetensors`/`*.pt`/`*.bin`)、数据集、episode cache、
  评测产物。**即使它看起来是"历史产物""中间态""已 NO_GO 的路线"**,也适用。
- 删除前必须逐项确认第二份副本**真实存在且完整**:目标路径可列出、文件数与字节数与源一致
  (或已通过 sha256 校验)。把校验结果写进 ledger,再删。
- **禁止用类别判断替代副本校验。** 2026-08-13 的教训:CPFS 清理把
  `data/psi0_runs`(803 文件 / 300GB,9 个 Ψ0 posttrain run)按 "historical intermediate"
  标签直接删除,没有留归档副本;当时唯一的另一份在即将下线的 qy_pi_ft 上,险些永久丢失。
- 另一份副本在**即将下线/无法长期访问**的机器上(临时集群、借用节点、到期实例)时,
  不算有效副本 —— 先把它搬到长期存储,再谈删除。
- 优先用"归档后删除"流程(rsync 到 OSS/长期盘 → 校验文件数与字节数 → 记 ledger → 删除 →
  在原位留绝对符号链接),而不是 `DIRECT_DELETE`。`DIRECT_DELETE` 只允许用于
  可从公开来源重建的内容(公开仓库、可重下的公开数据集、包缓存),且要在 ledger 里写明重建方式。
- 清理脚本必须有保护名单(FORBIDDEN_PREFIXES),且新写入的抢救/交付目录要先加进保护名单
  再开始写,避免"边搬边被扫走"。
<!-- END WEIGHTS_DELETE_SAFETY -->

<!-- BEGIN DELETE_SAFETY_POLICY (managed block, edit via installer only) -->
# 删除前必须核实副本（权重/数据类目录）

事故背景：2026-08-13 一次清理把 `psi0_runs`（803 文件 / 300 GB）与
`simple_openfaucet_rollout`（27,845 文件 / 13 GB）按 `DIRECT_DELETE` 直接删掉，
当时唯一的另一份副本在一台当天正在下线的借用机上，两者都差点永久丢失。
根因不是"没意识到重要"，而是**用类别标签（"历史中间态"）替代了副本校验**。

- checkpoint、`*.safetensors` / `*.pt` / `*.ckpt`、数据集、episode cache、评测产物：
  **一律走"先归档、后删除"，禁止 DIRECT_DELETE**——哪怕标签是"历史中间态"、
  "临时产物"，哪怕对应技术路线已判 NO_GO。当前判定 NO_GO 不等于将来不需要复查。
- 删前必须逐项核实第二份副本**真实存在且完整**：比对文件数与总字节数，关键件比对 sha256。
  核实结果写进 ledger/回执。**禁止用目录名、类别标签或记忆代替实际校验。**
- **临时机、借用节点、到期实例上的副本不算有效副本。** 先搬到长期存储，再谈删除。
- `DIRECT_DELETE` 仅限可从公开来源重建的内容（公开仓库、可重下的公开数据集、包缓存），
  且必须在 ledger 写明重建方式。
- 新建的抢救/交付目录要先加入清理脚本的 FORBIDDEN_PREFIXES 保护名单，再往里写数据，
  避免边搬边被同一轮清理扫走。
- 空间告急时的正确顺序：先统计、报给人、拿到确认，再执行；不要在无人值守时段自行删除数据。
<!-- END DELETE_SAFETY_POLICY -->

<!-- BEGIN JOINT_ORDER_POLICY -->
# 关节顺序铁律(2026-08-24 确立,同日以 interface 文档勘误)

- **checkpoint 的关节序以其随附接口文档/导出配置为唯一真值**。ScaleBFM model_38000 的顺序
  由 `fsq_scaletrack_vla_interface.md` §2.1 明确规定为**串行序(即 MuJoCo 模型序,也是 action
  输出序)**:左腿6(hip_pitch/roll/yaw/knee/ankle_pitch/ankle_roll)→ 右腿6 → 腰3(yaw/roll/pitch)
  → 左臂7 → 右臂7。**不是** IsaacLab 交错 BFS 序——"IsaacLab `joint_names=[".*"]` 无
  preserve_order = 交错序"只是常见情况,articulation 顺序取决于具体 USD 资产,不核实资产
  禁止套用(2026-08-24 曾据此误判并重建出错序产物,已废弃)。
- 跨模块传递关节量一律**按关节名映射**,禁止按位置拷贝;两套顺序(串行 vs 交错)并存的项目里,
  每个接口边界都要写明所用顺序。
- parity/数值一致性测试若两侧共享同一套顺序假设、输入是合成随机数,测不出错排。任何顺序
  变更后必须补语义行为检查(真实站立观测 → 输出接近 default、左右对称、前后倾摄动响应反对称)。
- 部署封装(torch.jit.trace/freeze、ONNX)把 default_dof_pos/action_scale/重排索引烧死进图,
  顺序错了产物即作废。取证与勘误记录:
  `sh_rtx5000:/mnt/home/lizekai/APA/h100tortx5000/SCALEBFM_JOINT_ORDER_FINDING_20260824.md`(含勘误)。
- ScaleBFM 资产对应关系:`/home/galbot/Downloads/fsq_scaletrack_vla_interface.md` 是同目录
  `model_38000.onnx` / `model_38000.pt` 的接口说明;文档提到的 baseline 开源仓库对应的
  HuggingFace ckpt(model_22200 等)只存放在 sh_rtx5000,仅作参考;实际部署只使用 model_38000。
  ONNX 输入为预构建观测(`policy(B,3,64)=[proj_gravity,ang_vel,joint_pos_rel,joint_vel×0.05]`、
  `policy_task(B,6,267)`、`action(B,3,29)` 归一化动作历史、`mode/mode_mapping`),历史从旧到新。
<!-- END JOINT_ORDER_POLICY -->
