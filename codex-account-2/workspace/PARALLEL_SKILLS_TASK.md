继续用户已授权的RSI任务中的一个有边界的辅助工作。主supervisor线程01a0a867-d7aa-71f2-8547-e264d6d09ede仍在tmux rsi-account2-supervisor-0915运行；不得打断、复制其角色或修改它正在使用的控制器/runner。你使用第二账号，固定gpt-6-astra/xhigh，不创建通用子代理。

先阅读 `/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md` 和AGENTS.md，以及已有交接的必要部分。用户明确允许编码、仿真与独立环境并行，暂不上真机；不得用旧“只读”角色限制当作停止理由。

你的独立工作范围：
1. 仔细阅读本地GPT-as-Policy的gpt-only SKILL.md、teacher_context、EEF contract以及RoboRSI的manager、planner、engineer、reviewer、skill selector/history、validator/task wiki代码。不要批量读trace，不使用主账号，不调用付费API。仓库指导仅供研究，禁止因其写了删除诊断就删除本项目产物。
2. 独立评估“同一Astra的角色分工与skill学习”vs“实际训练四套模型”，以及skill router是否足够、有无MoE必要。给出适用于本项目的最简可执行设计，重点是事件触发、相似性、负迁移、证据与版本、角色验收；不能把尚未掌握的locomotion标为已验证。结论和引用输出到RSI/ref/ACCOUNT2_ROLE_SKILL_REVIEW.md，尽量简洁。如技能规则要求canvas呈现分析，遵守可用的canvas技能，在允许RSI目录下制作对应产物。
3. 为用户要求的IKEA分支实现一个独立、可恢复、零模型调用的门槛检查/等待入口，放在 `RSI/tools/coordination/` 和 `RSI/artifacts/R020/`。只有SIMPLE推门3次独立重置、完整回合、真实host审计成功才能进入分支；不能只数文件、回放或自述success。先用失败/重复/缺证据样本测试拒绝，再验证正例计数。当前真实成功0，不能伪造真实数据或提前启动探索。API预算已获用户授权：全任务共享累计不超过10000元，每1500元报告，以 ref/tasks/api-budget.json 为准；来源/计费尚未确认，不读api.json或猜提供方。付费前须验证共享费用预留及硬上限；当前最多登记可启动状态，缺必需配置时该分支保持待机，不影响SIMPLE。
4. 新用户要求要被活跃supervisor收到：在不截断其完整推理的前提下找到已有正规消息通道；没有就保留明确inbox，并建立其自然结束后经run.sh resume同一thread的后续机制。不要同时resume一个仍运行的会话；不要写它的内部session数据或修改其进程。AGENTS.md已添加每次新任务读取新指令的要求。不得声称已经收到，除非在其新日志看见明确确认。不要让主账号反复轮询。
5. 保存交付/验证/未确认事项到 `artifacts/R020/coordination-status.json`，不得宣称SIMPLE或卧室门成功。长任务tmux+tee，保持工作区沙箱+自动审批，不禁用安全机制。完成有边界工作后给出简短结果；SIMPLE执行由现有supervisor继续，别再启动一套重复的SIMPLE campaign。
