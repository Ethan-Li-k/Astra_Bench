# SIMPLE 六任务 skill 评审(对照 ref/GPT-as-Policy)

日期:2026-09-16。作者:评审侧 Claude 会话(只读评审,未改任何 skill、release、runtime)。
对象:`skills/releases/central-20260916-v4`(core + 六个 task snapshot + deltas + atomic-index)、
`skills/loco-manip-{core,simple,direct}/SKILL.md`、`tools/learn_grasp_skill.py` 的 immutable runtime 文本、
R019 回合证据(xmovepick 4/5、xmovebendpick 3、handover 1、door 20)。
参考:`ref/GPT-as-Policy/hybrid_rollout/robodojo/skill/SKILL.md`(831 词)、
`robodojo-gpt-only-rollout/SKILL.md`(560 词)、`context/teacher_context.md`、`context/eef_control.md`、`gate_prompt.md`。
榜单:https://psi-lab.ai/SIMPLE/index.html#results(9 方法 × 6 任务 × L0/L1/L2 各 10 回合)。

## 1. 结论

现有 skill 已吸收 GPT-as-Policy 的核心纪律:持久同回合上下文、动作绑定最新观测与唯一 request_id、
ACK/target_reached 不等于到位、闭合命令不等于抓住、rollout_finished 才终止、NOTES 记忆。
差距不在纪律,而在**结构与信息密度**:

- GPT-as-Policy 是三层:`SKILL.md` 只写流程与决策(编号步骤、精确工具名、精确数值界),
  `context/*.md` 放任务知识与本体合同,`gate_prompt.md` 放判据;SKILL 通过链接按需读取。
- RSI 把本体合同、观测规则、否定清单、终止合同、任务 delta 全部塞进一个受
  831 词/6250 字上限约束的文件。结果:v4 六个任务 SKILL 的前 6 段(约 375 词)逐字相同,
  真正任务相关内容只有末尾一段(约 100–130 词);而 actor 真正需要的数字
  (单点 ≤0.03 m、连续 2–5 knot ≤3 s、腕段 ≤0.06 m/总 ≤0.20 m、踝 ≤0.30 m、转 0.10 rad/段、
  时长 0.5–3 s、原生成功判据、桌面高度)在 skill 里一个都没有,只散落在观测 payload 和 actor 自己的 NOTES 里。
- 核心 skill 约四成句子是否定句("X does not prove Y")。GPT-as-Policy 也有这些,但先给正向流程,
  否定句集中在末尾。

## 2. 证据(来自本地回合记录)

| 证据 | 数据 | 对 skill 的含义 |
|---|---|---|
| 动作状态标签无区分度 | xmovepick5 成功回合 35/35 动作 `timed_out`;xmovebendpick3 成功 48 timed_out/19 reached;door20 成功 22/17 | skill 花篇幅写"Interpret timeout by phase",但标签本身几乎不携带信息;应改为按 `actual_position_error_m_by_link`/旋转残差判断 |
| 成功回合的关键机制未进中央 delta | xmovepick5:局部前轴 roll 误差 0.021 rad(世界轴 0.16–0.25 rad);双腕协同横移才解决向内饱和;单侧踝抬高参考每动作降骨盆约 3 cm、落地参考回升 | v4 `deltas/xmovepick.md` 只写了否定("elevated ankle references … are not a crouch primitive"),没写正向条件与副作用 |
| 失败回合的机制 | xmovepick4:240 s 双手全程张开,右手低位可达饱和在 z≈0.69–0.72,目标面 z≈0.51–0.54 | delta 应给"可达高度带"这种几何参考数(类似 GPT-as-Policy 的 +0.1311 m pad 参考) |
| Handover 原生判据与任务不一致 | 原生 reward 每次判定"盒在容器内"+0.1,≥0.9 即成功,不要求松手;Handover1 在第 47 动作左手仍握着时触发,回合结束,未释放 | 学习期:原生成功只是事件,必须继续到释放+手离开+稳定;冻结原生评测:盒进容器即计分。两种语义都要写进 delta,让 actor 知道自己在优化什么 |
| Mobile P&P 原生判据 | 每次判定"在容器内且无手接触"+0.02,≥0.4 即成功(需连续 20 次) | 与 Handover 相反,必须松手;delta 里没写 |
| 榜单目标物与学习目标物不同 | XMovePick 官方 DR 目标 cracker_box0,学习用 apple12;Grasp 官方 chips_can10,学习 apple12 | xmovepick delta 里的"H001004 side grasps… apple"在 L0/L1/L2 会误导 |
| 原生步数预算 | max_episode_steps:XMovePick 800、BendPickMP 400、Handover 800、Grasp 800、Mobile 1200;学习期 harness 用 240 s 或 None | skill 没有 GPT-as-Policy 那句"Track step_id/max_episode_steps, reserve steps for the finish";冻结评测前必须核对控制步长并写进 skill |
| 六份 task SKILL 结构不一致 | xmovepick、xmovebendpick 两份是学到的完整 v3 原文(frontmatter 说明各异),其余四份是 core+delta;`loco-manip-simple` 与 `loco-manip-direct` 除末段外逐字相同且 frontmatter 同名 | 不是用户要求的"一份短共同合同 + 六个 delta";retrieval-labels.json 六份全为 `{}` |
| 锻炼/正式协议差异 | 当前全部 MuJoCo、推理时物理暂停、非 Isaac 视觉;官方 10 回合 × 3 级用 Isaac 渲染与原生 TimeLimit | skill 不能解决,但 skill 需要为"推理期间物理是否推进"两种模式各留一句合同 |

## 3. 建议

### 3.1 结构(对齐 GPT-as-Policy 三层)

1. 把本体合同抽成 `CONTROL_CONTRACT.md`(项目里 `.cursor/skills/loco-manip-four-point-policy/CONTROL_CONTRACT.md` 已有雏形),
   内容:四个命名点与世界系/wxyz、active/inactive 语义、单点与连续 chunk 的具体数值界、closure 0/1 语义、
   50 Hz tracker/物理暂停、相机内参合同、五个几何工具的名字与"只算不动"语义。SKILL 用一行链接引用。
   上限只约束实际加载的 SKILL+runtime,链接文件按需读取,这与 GPT-as-Policy 的做法一致;需要框架 owner 明确登记
   "加载文本"与"按需文本"的边界并 hash。
2. 把"X 不能证明 Y"的否定清单压缩成一个 ≤6 行的"证据规则"块,放在流程之后,不再散落在每段。
3. SKILL 主体改成编号流程(GPT-as-Policy 的 1–4 步风格):
   `loco_start` → `experience_select` → 观测/几何计算(点名工具)→ `scalebfm_act` 一个 chunk → 读 by-link 残差与 RGB → 更新阶段账本 → 回到计算;
   终止段只写:原生里程碑是事件、rollout_finished 才停、`finish_attempt` 记 stall 不终止、`skill_update` 是提案。
4. 六个 task SKILL 统一为"core + delta"生成,xmovepick/xmovebendpick 的学到 v3 内容拆成 delta 与 atom,不再整份放 snapshot。

### 3.2 阶段账本(借 gate_prompt 的 task_progress)

在 NOTES 与每个 `reason` 里强制维护
`verified_completed / currently_attempting / remaining`,阶段名与 host 审计的
`independently_verified_stages` 用同一套词:
`approach → stationary_reach → open_enclosure → closure → probe_lift → separate_hold → (present → receiver_enclosure → load_transfer → giver_clear) → loaded_travel → lower → release → hands_clear_supported`。
每阶段写"进入证据 / 退出证据 / 丢失时回退到哪一阶段"。这是 Handover1、Mobile Cheezit1 两类失败的直接对策,
也让 actor 阶段与审计口径一致。替换现有的"当前问题/总目标/不可重犯的错误"三行(用户已取消该模板)。

### 3.3 每个 delta 必须包含的六项(现在都缺 2–4 项)

1. 原生判据一句话(见 §4 表),并标明学习期与冻结期的语义差异。
2. 目标物类别与形状(cracker box / chips can / apple),按类别写包络策略,不按任务名。
3. 表面/桌高名义值与已实测的可达高度带(例:目标面 z≈0.53 需要骨盆 ≤0.73;右手低位不降骨盆饱和于 z≈0.69–0.72)。
4. 正向条件机制(局部前轴 roll、双腕协同横移、单侧踝参考降骨盆及其副作用与恢复),写成"条件→动作→可观测结果",不写坐标。
5. 预算:原生 max_episode_steps 与 harness 预算各一行,并要求预留收尾阶段(GPT-as-Policy 的 reserve steps)。
6. 三个来源 ID 与不适用条件(现有做法保留)。

### 3.4 locomotion 原子

十次推门与两次 XMovePick 成功都用了同一模式:一侧踝前移 0.15–0.26 m + 双腕同向前移、另一踝落地参考、
骨盆高度 ≥0.75 且倾角 <15° 后再换另一侧。它至今只以"not a validated gait"的否定形式出现。
建议在 atomic-index 里加 `stepping_approach_unloaded` 原子(前提:空手、目标距离、地面平),
把进入/退出证据写清;Mobile P&P 的 `loaded_travel` 单列为未验证探索,不与空手步进混用。

### 3.5 harness 侧配合(不改 skill 语义,但决定 skill 能写多短)

- 观测回执把 `timed_out/target_reached` 换成或补充 by-link 残差与容差判断;skill 就不必解释 timeout。
- 观测里直接给当前任务的 `native_max_steps / steps_used / harness_budget_s / sim_s`,对应 GPT-as-Policy 的 `remaining_steps`。
- 学习期 Handover 类"原生成功但未释放"的续跑 wrapper 已在用户合同里,skill 里配合一句即可。

### 3.6 与榜单对齐前 skill 无法弥补的前置

L0/L1/L2 的实际 DR 参数、Isaac 视觉输入、原生 TimeLimit 单位、目标物身份这四项未核实前,
任何 skill 改动都不能宣称榜单成绩;这四项每一项都会改变 delta 的第 1、2、3、5 条。建议先把这四项写成
`task_specification` 的固定字段,再生成 delta。

## 4. 六任务原生判据 vs. 当前 v4 delta 覆盖

| 任务(精确 env_id) | 原生判据(源码) | max_episode_steps | 官方目标物 | v4 delta 是否写明判据/目标物/高度带 |
|---|---|---|---|---|
| XMovePickTeleop | 抬升 ≥0.9×0.10 m | 800 | cracker_box0(学习用 apple12) | 否/否(写的是苹果)/否 |
| BendPickMP | 抬升 ≥0.9×0.10 m | 400 | cracker_box0 | 否/否/否(仅"low reach") |
| HandoverTeleop | 盒在容器内累计 9 次判定,不要求松手 | 800 | cracker_box0 | 否(写了"early native finish"但没说机制)/否/否 |
| LocomotionPickBetweenTablesTeleop | 在容器内且无手接触累计 20 次判定 | 1200 | cracker_box0 | 否/否/否 |
| TabletopGraspMP | 抬升 ≥0.9×0.02 m(1.8 cm) | 800 | chips_can10(学习用 apple12) | 否/否/否 |
| XMoveBendPickTeleop | 抬升阈值同类(8–9 cm) | — | cracker_box0 | 否/否/否 |

Psi0 官方成绩:XMovePick 10/10/6、BendPick 10/10/10、Handover 7/7/10、Mobile 7/5/6、Grasp 10/10/8、XMoveBendPick 10/9/9。
本地当前:六项固定候选稳定性全部 0/5;学习期审计成功 XMovePick 2(均 H001004 辅助)、XMoveBendPick 1、Handover 0、Mobile 0、BendPickMP/GraspMP 尚在控制适配。

## 5. 不建议做的事

- 不把 RoboDojo 的 1–5 步/5 cm/0.35 rad 数字移植为 ScaleBFM 参数(用户已禁止);但要把本项目自己的数字写进合同文件。
- 不为 MoE/多角色扩 skill;先把六个 delta 补齐上述六项。
- 不在 skill 里加入任何 host 侧物体真值(原生判据是公开任务定义,不是隐藏状态;可以写)。
