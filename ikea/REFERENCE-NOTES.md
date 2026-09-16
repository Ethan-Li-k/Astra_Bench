# 参考阅读与迁移边界

GPT-as-Policy本地全部12个.md已读，逐文件SHA和长度见reference-index.json。以下仅作为工程索引，不整包注入actor：

- `README.md`：reference overview; report/UI/licensing not actor input。
- `hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md`：short actor entry。
- `hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md`：embodiment-specific units/EEF/ACK contract; do not copy robot offsets。
- `hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/teacher_context.md`：predecessor evidence and uncertainty。
- `hybrid_rollout/robodojo/skill/SKILL.md`：short actor entry。
- `hybrid_rollout/robodojo/skill/context/eef_control.md`：embodiment-specific units/EEF/ACK contract; do not copy robot offsets。
- `hybrid_rollout/robodojo/skill/context/teacher_context.md`：predecessor evidence and uncertainty。
- `hybrid_rollout/robodojo/skill/gate_prompt.md`：hybrid outcome/intent gate; pi05 requirement not applicable to Direct。
- `hybrid_rollout/robolab/skill/SKILL.md`：short actor entry。
- `hybrid_rollout/robolab/skill/context/eef_control.md`：embodiment-specific units/EEF/ACK contract; do not copy robot offsets。
- `hybrid_rollout/robolab/skill/context/teacher_context.md`：predecessor evidence and uncertainty。
- `hybrid_rollout/robolab/skill/gate_prompt.md`：hybrid outcome/intent gate; pi05 requirement not applicable to Direct。

NOTES/history是每回合生成的公开记忆/执行记录；本地参考仓库未提供原运行历史，不能补造。首套餐回合NOTES写入被其只读工具环境拒绝，公开selection/action/stall/skill记录仍保存其判断；API以public_history_index及逐请求public_decision保存。

控制相关重点：EEF位置不是TCP；单位/四元数/夹爪方向必须按机器人合同；ACK与目标不是到位/接触证据；Direct在rollout_finished=false持续同一reset。RoboLab Panda和RoboDojo X5的固定偏移不可搬到G1。hybrid的pi05前置与每chunk gate不适用于本Direct。参考的900秒/两次continuation上限不搬用。

RoboRSI参考：base/move_ee_delta/libero/SKILL.md用于小动作与测量反馈的分离；atomic/place_can_basket/SKILL.md用于前置条件与完成证据；long_horizon/clean_table/SKILL.md用于按阶段组合而非把未完成子目标跳过；agents/task_wiki.py区分失败事实、待审假设和晋升证据。外部参考角色调用和人工批准规则不覆盖当前用户授权；这里只事件触发审查，不每chunk多角色调用。

本地框架组合候选已进入runtime-v1/v2：skill+runtime总长度受限，审计未知/否决不得成功优先。唯一shared core发布者未改。条件化共享路线是控制合同→locomotion→交互机制→任务实例；目前不宣称可靠行走或神经MoE。
