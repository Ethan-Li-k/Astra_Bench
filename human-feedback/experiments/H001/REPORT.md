# H001：三回合自主纠正已完成，抓持目标仍未解决

完成3次独立native reset、55个新纠正动作、98.64秒新增物理执行；没有确认抓持或入碗成功。三次原动作1–59重建不计新增尝试。第1回合实际闭合和抬升未抓住；第2、3回合因包络未决始终张手，直到物理预算结束。不能合称“三次抓取终态物理失败”。全部分母保留，停止新增纠正回合，交主线程判断下一步及是否达到人工求助门槛；本分支没有向用户提问。

## 已检验的变化与结果

1. **trial-001，反馈001–003，16动作/28.32秒。** 候选侧抓；先下降后分级闭合，再依据新图修正XY/深度和实际姿态。两次抬升探针及最后独立1.5秒观察均未确认苹果离桌。末次腕实际升24.94mm，苹果仍留桌。终止为有物理失败证据后的actor主动结束，native仍in_progress，剩余6.04秒。闭合最大命令0.5；不将命令或到位当抓持。
2. **trial-002，反馈001–004，22动作/34.52秒。** 004在回合1完整自然结束后才收到并采用，禁止包络未确认时以小幅闭合试探。本回合先校高度再改善视野，全部张手。第14新动作、21.06秒处有完整可见近侧拇指记录，随后位置调整又造成裁切，包络始终未确认。终止physical_budget，native仍in_progress；抓持、抬升与保持均未测试。
3. **trial-003，反馈001–004，17动作/35.80秒。** 同004门槛，仅主要改变获取顺序：在较高位置先取得手指视野，再校高度/深度。第5新动作、8.04秒处双目已完整可见近侧拇指，经原图复核；后续后移、降低和实际姿态漂移又丢失视野，最终仍未确认包络。全程张手，physical_budget结束，native仍in_progress；抓持、保持未测试。

有限改善是**本次“先视野后校高”的动作序列更早取得可见指面**，不是已提升抓持成功率。每种顺序仅一次，后续可见性仍不稳定，没有独立复验或跨布局迁移结论。没有抓持成功可供成功复验。

## 视频

所有录像均来自新MuJoCo物理执行，25fps。完整左目视频含固定前缀和全部新动作；纠正片段含分叉前约3秒及全部纠正动作。不是快照拼接，不把导出或播放计成新试验。

- 回合1：[完整左目](evidence/trial-001/full-head-left.mp4) · [纠正片段](evidence/trial-001/correction-head-left.mp4) · [诊断视角+左目全程](host_audit/trial-001/video/episode.mp4)
- 回合2：[完整左目](evidence/trial-002/full-head-left.mp4) · [纠正片段](evidence/trial-002/correction-head-left.mp4) · [诊断视角+左目全程](host_audit/trial-002/video/episode.mp4)
- 回合3：[完整左目](evidence/trial-003/full-head-left.mp4) · [纠正片段](evidence/trial-003/correction-head-left.mp4) · [诊断视角+左目全程](host_audit/trial-003/video/episode.mp4)

诊断视角和host叠字未给actor；策略每步使用原左右目PNG，保存在各trial/public/rollout/episode/observations。完整视频和代表片段已解码验证；每段来源、起止时间与裁剪命令见evidence/trial-*/video-provenance.json。

## 对照、版本和时间合同

后端是**SIMPLE / MuJoCo**，不是Isaac；同步暂停物理等待Astra，**非RTC**。每回合native seed=3 reset、checkpoint站姿、250次稳定控制，接原动作1–59；不使用状态teleport。动作59结束于sim210.645s，稳定后初始为5.005s。三次固定前缀各10283个记录采样的时间、四点、reference、关节qpos、mocap、控制链和状态字段完全匹配冻结基线；动作59双目哈希均相同。不能据此宣称全部历史外部依赖或未记录隐藏状态逐位一致。

原model_38000 SHA256：d87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa。复用冻结live.py、policy_harness.py、simple_live.py及依赖；三回合物理控制源码哈希完全相同，没有迁移碰撞/主控版本。MuJoCo3.3.6、NumPy1.26.4、ONNXRuntime1.23.2、Gymnasium1.2.3，既有环境只读复用。基线610个冻结文件在执行前、完成后均哈希核验通过。

控制保持UMI-4、物理200Hz、tracker50Hz、0.03m/0.10rad每步、0.5–3s动作时长、duration+2s跟踪timeout。原240秒物理预算含固定前缀，分叉后剩34.36秒。原runner语义是完整有界动作后检查总预算，所以第2/3回合分别超出0.16/1.44秒；真实时间完整保留，不声称精确中途截断。模型推理等待无截止、无延迟重发，单列于actor_input_audit；模型自然turn/completed后才关闭进程。

全部模型进程经指定codex-account-2/run.sh启动，连接回执核对gpt-6-astra/xhigh且禁止fallback；无付费API，无真机执行。没有新安装或修改既有环境，没有修改正式apple/door campaign，正式成绩增量0。全部是**原策略前缀固定的人工反馈辅助诊断**，完全自主从reset新任务数量0；human_feedback_used=true，human_demonstration_used=false。

## actor输入与host评估隔离

公开来源是原任务、原apple短skill、原GPT-as-Policy短skill参考、原1–65动作及公开观测、人类原话、当前双目/标定、命名机器人本体/指几何，以及自己此前公开经验。见public/sources、每回合public/actor/rpc_calls和host_audit/trial-*/actor_input_audit.json。任意shell/文件图像工具关闭；evidence_read只允许运行所列公开目录，calculate限纯数值，动作只有冻结四点接口。越界路径、读取host/账号以及计算工具文件访问测试均被拒绝。

三回合公开JSON未发现host状态、contact或reward/native outcome字段；实际已完成工具类型只有受控动态工具和对话项目。host物体/接触审计、原生结果、诊断录像只保存在host_audit及外部交接元数据，后续actor只读先前trial/public。每次闭合许可是actor自己的可见证据声明，host不以真值替它认证。

host审计中三个回合苹果最高变化均不足2e-11m、无持续离桌，20ms采样未见手-苹果接触；这支持未取得抓持，不单独确立根因，也不排除采样间短暂接触。真实新动作参数与理由全部由Astra选择，工程师未提供成功轨迹或物体坐标。

## 保留经验与适用边界

- [候选1](candidates/trial-001.json)：降低、二维覆盖和mesh范围不足以证明侧抓包络；需实际离桌共动及独立保持。适用于本次近水平侧抓，不能复用数值下降/XY/闭合为成功配方。
- [候选2](candidates/trial-002.json)：004要求先确认包络，未知时保持张手；禁止试闭合绕过前置。只验证了该行为约束执行，没验证成功率提升；不适用于把顶抓强制成掌心等高。
- [候选3](candidates/trial-003.json)：获取指面视野须同时保持苹果与整个开口的相对深度；下降、后退或姿态漂移后重验。仅看见拇指不充分，未看见也不等于必定抓空；未验证跨布局或其他抓法迁移。

原skill v001为556words/4017chars，v002为671words/4855chars，三份候选含适用/不适用条件均低于831words/6250chars。版本、反馈采用时刻、经验来源和失败保留，见versions、feedback004-adoption.json及short_rule_length_checks.json。所有规则仍是候选；没有训练GPT权重或发布共享skill，SIMPLE supervisor仍是唯一共享发布者。

## 重复现象、未解问题与交接

重复的是包络获取瓶颈：为显露近侧手指而改变位姿后，开口深度/高度仍未对齐；随后校正又造成裁切和实际姿态漂移。平移误差可以只有毫米级，姿态仍超到位阈值。以上是跨回合观测，不是已确证的单一物理根因。

尚未解决：如何从现有公开信息联合确认侧面高度、深度和实际手姿；同一控制器能否维持既对齐又可见的接近；固定前缀只留下34.36秒是否限制修正；真正满足004包络后，闭合接触与保持表现如何。没有004合规的闭合/抬升数据，不能先归因摩擦、力或接触面。

已完成授权的最多3个新物理纠正回合，但其中只有1次实际闭合/抬升、2次为004下预抓取预算结束；不能据数字3自动认定达到“三次同因抓持失败”的人工求助条件。交主线程审查，不直接向用户求助，不自动开始第4回合。

机器交接入口：[status.json](status.json)、[COMPARISON.json](COMPARISON.json)、[MAIN_THREAD_NOTICE.json](MAIN_THREAD_NOTICE.json)。每回合完整版本/初态在host_audit/trial-*/version.json与initial_state.json，公开输入回执和候选、host评估分别保留。原始请求及所有失败、成功数为0的分母均未改写。
