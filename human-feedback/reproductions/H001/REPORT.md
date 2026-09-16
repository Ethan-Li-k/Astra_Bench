# H001 有边界物理复现

已从 SIMPLE 原始 seed=3 reset 连续执行 episode-0003 的原动作 1–65，复现闭合后两次抬腕未带起苹果。新执行后端为 **SIMPLE / MuJoCo**；不是 Isaac 物理，也不是状态回放冒充物理。`reproduction_only=true`，`task_success_credit=false`。未创建 GPT actor、子 agent 或 campaign，未调用付费 API，未执行纠正实验。

运行由已有第二账号会话管理，观测到 `CODEX_HOME=/home/galbot/lizekai/RSI/codex-account-2/home`，指定 `gpt-6-astra/xhigh`。确定性旧动作重执行没有新增 GPT 推理，不读取凭据。全部新增文件位于本目录。

## 证据与匹配程度

- [原动作 1–65](source_commands/actions.json) 的请求内容与原回合逐一一致；只重定向输出及最新 observation 路径。人工反馈只用于确定本次审查范围，没有改写基线动作。
- 任务定义取自原 episode 的 `agent/workspace.json`。原场景配置、Sonic/PD 配置和 policy 关节名顺序完全一致。checkpoint 站姿、seed=3、250 次稳定控制均保留；原始 reset 内先推进 0.005 s，稳定后为 5.005 s。
- 动作前缀结束于 219.765 s；动作期间实际推进 214.760 s。物理步长 0.005 s，tracker 周期 0.020 s。保留 10,739 个初态／动作采样点和包括稳定阶段在内的 10,988 次 tracker 输入历史。
- 所有记录采样点的命名关节状态、四点位置、reference、闭合命令、控制输出、执行状态和仿真时间逐值一致；未观察到实质性动力学发散。
- 132 张原相机 PNG 中，123 张哈希一致。其余 9 张差异低于冻结的图像阈值；动作 **59–64 的全部左右目图哈希一致**。最早图像差异和完整数值审计仅存放于 `host_audit/`。
- 预先固定的失败判据在原轨迹和新轨迹均成立：闭合后腕部明显抬升，苹果没有随之离桌，未获得 native success。实际图像同样支持“未验证抓持／未带起”，但不能独立确立某一种接触机制。

阈值在物理执行前写入 [thresholds.json](thresholds.json)，执行后未改动：初态位置 1 mm、初态关节角 0.005 rad；轨迹四点位置 5 mm、自由关节位置 2 mm、关节角及自由关节姿态 0.02 rad、时间差 20 ms。另有控制输出及图像阈值，完整定义见文件。哈希为 `56e5d11bece72b5fd23f289a81a68defca418b9554ec229efaf0b98b295d9c78`。任何实质发散都必须停止同条件／因果归因，本次未触发。

## 版本与完整状态的限制

原记录提供 qpos、mocap 和控制输出，未保存完整 qvel、接触求解 warm-start、tracker 历史和腕部 PI 状态；没有使用第 59 帧 qpos teleport。已从历史副本中恢复哈希与原回合完全一致的 `live.py` 和 `policy_harness.py`，model_38000 adapter、`simple_live.py` 和手指几何模块也匹配原哈希。模型实际 SHA256 为 `d87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa`。

原 `simple_environment.py`、`simple_recording.py` 的确切旧源码未在检索范围内找到；使用本目录隔离冻结的兼容版本。原 learning wrapper 未运行，复现直接使用同一工具 host／harness 控制接口。外部 SIMPLE／依赖库版本和资产原始哈希没有完整历史记录；当前导入源码、读取资产和编译模型另行保存。尽管全部可对照物理轨迹一致，**不宣称历史完整隐藏状态或全部依赖逐位同一**。新轨迹的速度、积分器及 tracker 历史已保留，选定 checkpoint 的范围有明确说明。

## 实际执行及文件

真实长命令在原 `rsi-h001-repro-0916` tmux 会话的新窗口内执行，并用 tee 保存日志，没有重复启动主任务：

```sh
tmux new-window -t rsi-h001-repro-0916 -n physics-002 bash /home/galbot/lizekai/RSI/human-feedback/reproductions/H001/run_physics.sh
```

启动脚本调用已有 SIMPLE `.venv/bin/python reproduce.py attempt-002`。完整命令见 [commands.jsonl](logs/commands.jsonl)，真实执行日志见 [physics-attempt-002.log](logs/physics-attempt-002.log)，退出码 0。逐动作回执、左右目 RGB 和机器人观测保存在 [attempt-002](attempt-002/)；完整物理、tracker、版本及差异审计保存在 [host_audit/attempt-002](host_audit/attempt-002/)。

- [新物理执行完整视频](host_audit/attempt-002/video/episode.mp4)：214.80 s / 5,370 帧，25 fps；含 host 诊断视角，不作为未来 actor 的额外输入。
- [闭合与抬腕的原头部相机片段](evidence/closure-lift-head-left.mp4)：13.84 s / 346 帧，从新物理录像提取；提取本身不是新物理试验。
- [关键原图及新原图索引](evidence/index.json)：像素未修改，左右目分开保留；包括动作 59、60、61、62、63、64、65。
- [动作 59 新左目](evidence/keyframes/0059/reproduced_head_stereo_left.png)、[动作 64 新左目](evidence/keyframes/0064/reproduced_head_stereo_left.png)。

保留了第一次工程失败：`attempt-001` 实际完成 250 次稳定控制且初态 qpos 完全匹配，随后审计用 `mj_saveLastXML` 对 SIMPLE 的编译模型报 `No XML model loaded`，尚未执行动作 1。通用 host 回执中的 `no_execution` 不能理解为没有稳定阶段物理；没有把它计为苹果失败复现。该次错误及源码旧版本保留；修复仅跳过不可用的 XML 导出，MJB 已保存。第二次运行控制参数、动作和阈值未变。

## 根因与下一实验

已确认的是失败现象可复现。用户提出“手掌高于苹果、拇指不可见，先下降至同一平面”仍为待检验假设；未将掌心等同于指腹／包夹区，未宣布用户根因已经证实。视觉高度判断、闭合几何、接触及遮挡各自的作用尚未通过干预区分；20 ms 记录也不能排除采样间的短暂接触。

本基线按 [BASELINE_FROZEN.json](BASELINE_FROZEN.json) 的文件哈希冻结。下一阶段说明见 [NEXT_EXPERIMENT.json](NEXT_EXPERIMENT.json)：先等用户澄清平面参照，再由主控或新授权续接；从同 reset 和原动作前缀开始，只改变闭合前的高度判断及其触发的张手下降，其他条件尽量固定，必要的后续高度锚点调整必须明示。策略只可获得 RGB、命名本体和用户语义反馈，不得读取 `host_audit/`。纠正回合须单列 `human_feedback_used=true`，本次没有运行。

`status.json` 为交接入口。没有修改公共反馈、UI、环境、原资产或共享 rsi/tools/skills；没有中断推门／其他正式任务，不增加任何成功数。

桌面通知已用本机兼容参数发送（退出码 0）；首次不支持 --print-id 的错误日志保留。系统接受通知不代表用户已阅读。完整录像及片段通过解码校验，tracker 采样周期检查通过；基线清单冻结 610 个文件。
