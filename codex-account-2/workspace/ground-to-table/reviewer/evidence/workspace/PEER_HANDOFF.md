# SIMPLE 并行任务确认（2026-09-16）

来源任务：codex://threads/01a0a4fb-3324-7073-b667-4e0e94c54ff2，simple开门branch。

对方继续SIMPLE推门及水龙头/苹果/抓盒，第二账号 supervisor 01a0a867-d7aa-71f2-8547-e264d6d09ede、tmux rsi-account2-supervisor-0915。共享core唯一发布者是该SIMPLE supervisor。本分支仅提交候选，不直接覆盖公共 skills/loco-manip-core/SKILL.md。候选须带控制器/代码/skill版本、任务机制、前置条件、when_NOT_to_use、成功与失败证据，交叉验证后才共享晋升。

既有第二账号角色研究 rsi-skill-review-0916 将产出 /home/galbot/lizekai/RSI/ref/ACCOUNT2_ROLE_SKILL_REVIEW.md 与 /home/galbot/lizekai/RSI/artifacts/R020/role-skill-review.canvas.tsx，目前尚未交付。检查产物是否真实存在再引用；不要重复整套研究。共同方向：冻结Astra、事件触发角色分工与显式skill router；没有验证权重训练或神经MoE。

最新可复用反例（仅工程诊断；不得注入视觉actor）：
- /home/galbot/lizekai/RSI/artifacts/R019/kinematic-reference-02/summary.json：可达IK参考在UMI-4/VR-5/Full-14均无完整足离地。
- /home/galbot/lizekai/RSI/artifacts/R019/ik-actuation-01/direct-IK-PD/result.json：直接IK-PD约1.04s失稳。
- /home/galbot/lizekai/RSI/artifacts/R019/foot-residual-01/VR-5/result.json：8Nm受限足端残差在VR-5仍未离地。

不能将这些结论泛化为所有setting不可走，不能重复相同诊断或把直接关节控制算正式成绩。SIMPLE推门仍0/10。对方正在做零模型的自然回合结束接续器，不中断推理，不并发resume同一thread。

本分支的开发推进、公开证据候选、障碍与接续信息写入PEER_OUTBOX.md；收到本交接后先检查USER_UPDATE.md，再继续地面红块任务。确保supervisor每次返回都留下明确状态，并在有安全相关下一步时接续工作。

## 更新：角色研究报告已交付

/home/galbot/lizekai/RSI/ref/ACCOUNT2_ROLE_SKILL_REVIEW.md 现已存在且已读。请复用该独立评审，只做本任务的适配与落地。重点：事件触发同一冻结Astra角色、显式router、逐回合pin版本、依赖hash与失败分母、共享候选单写入者；RoboRSI部分auto_apply跳过harness、共享文件临时覆盖有竞态、long-horizon reviewer权限含GT，不能照搬。不得删除旧诊断。独立Reviewer检查实际原始证据而非只读Engineer总结。
