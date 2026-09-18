# ENPIRE 借鉴与 RSI 生效范围

用户要求参考本地 ref/ENPIRE 的 reward、成功/失败学习及其他可复用设计。GPT-as-Policy 仍是第一优先级，RoboRSI 的任务树/经验复用原则保留；ENPIRE 补充验证与复盘流程。API 停用和禁止主账号不变；本轮不调用新模型、不启动真机。

新增 supervisor skills：skills/reward-review/SKILL.md、skills/experience-learning/SKILL.md。它们用于管理/审查/发布环节，不隐式塞进 actor 上下文，不绕过 831 words / 6250 characters / 5357 非空白的加载上限。当前仍是同一 Astra 的分工与确定性宿主工具，无须为此训练四个独立模型或引入 MoE。

采用：子条件诊断；事实/判据/归因分离；原生结果、完整任务审计、阶段进展分别记录；成功与失败对照；按机制命名与版本化；单个可证伪假设；异步证据绑定到原始观测和动作；冻结验证器；完整失败证据保留。

调整或拒绝：一次 native success 自动证明所有前置步骤；一次调用成功即视为成熟 skill；固定 80% 分界和有失败必改代码；把未调用阶段算失败；跨 run 清空经验；仅看最终帧；把特权物体状态给 RGB actor；覆盖裁剪原始视频。已有独立成功门槛和候选隔离保持有效。

最小实现：rsi/evidence_review.py 只投影已有审计，不新造成功、不重写 reward/result。网页观察器为终态产出带来源 hash 的只读复盘包。Mobile progress v2 保留跨掉物/重抓的历史最佳持物进度，重复已走过的路段不再刷新停滞计时。该修改由反例测试验证；新物理学习效果尚待新回合加载。
