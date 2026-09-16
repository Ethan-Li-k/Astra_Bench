# IKEA 持续执行任务（专属辅助账号）

你是本任务独立工程/探索执行者。请立即实际推进，不只交付计划。所有模型固定 gpt-6-astra/xhigh；套餐只能通过 `/home/galbot/lizekai/RSI/codex-account-2/run.sh`，付费复用已验证的 llm-gateway.galbot.com 传输与唯一共享预算。不得启动主账号或自动消费重置券。新增写域 `/home/galbot/lizekai/RSI/ikea`；外部资产/环境只读使用，必要独立环境也放该目录。不删除任何数据。长命令用 tmux+tee，不设置模型推理超时，不打断/重发在途模型请求。

每次决策先写当前问题、总目标、不可重犯的错误。先读 RSI/AGENTS.md、ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md、HUMAN_FEEDBACK.md、IKEA_OWNER.md。IKEA_OWNER 是最新用户授权：现在开工，不等旧门槛；事实上SIMPLE已有5审计成功。任务顺序：棕色卧室门→抓桌面苹果→开冰箱→抓苹果/开冰箱/放入的组合。优先Isaac；现有本地MuJoCo可作明确标注的适配与探索，不能称为Isaac或原样USD结果。正式执行沿用 model_38000 UMI四点ScaleBFM，与实际接口按名映射关节。

## 已知资料，直接复用

- 用户照片 ref/tasks/20260915-210156.jpg。只读原资产 /home/galbot/Downloads/APA/IKEA_LivingRoom_Mesh_0915。
- `artifacts/R023/ikea-door/asset-feasibility-after-preview.json`、fbx-structure.json、fbx-scene.assxml、preview-05/west-wall.png；`tools/preview_ikea_fbx.py`、inspect_ikea_usd.py。Door_West已静态对应，469节点141mesh，门/把手分离，FBX转米坐标(x,-z,y)*.01。现有USD22.11不兼容Unicode prim，先前已做有界工具检查，不重复无限探索；FBX静态预览已完成。艺术家pivot只是物理假设，不是铰链/锁舌真值。可在新写域建立明确标注的派生物理场景，保留原几何、单位、初态与物理参数差异。
- `ref/ACCOUNT2_LIVE_CONTINUE_20260916.md` 给现有环境/控制/视频管线；SIMPLE主控使用辅助线程 01a0a867-d7aa-71f2-8547-e264d6d09ede，shared core唯一发布者。不要改它的campaign/共享代码/continuation。先将接管信息队列送达，获取ACK；自己只写ikea，避免重复同目标环境。
- 成功推门 `artifacts/R019/door-campaign/episode-0012` 到0014与其SKILL/experience/success_review；是明确碰撞修复变体，不是原样CloseDoor。桌面抓块R018十成功、SIMPLE bendpick episode0006一成功。读取公共skill/动作/图像与版本可复用，host审计只验证成绩，不能把隐藏物体姿态/关节真值/奖励/接触写入actor经验。
- API物理传输 `api-ground-to-table/actor-adapter`，预算 `tools/coordination/shared_budget.py`、`api-ground-to-table/empirical_hook.py`、`artifacts/R020/shared-budget-ledger.json`、`artifacts/R021/api-ground-002/batch.json`。不要修改在途原actor，IKEA独立适配。账本由现有组件原子并发预留，全分支合计10000元，每1500汇报，未知费用保留。最新用户禁止再次调查费率余额；已有预留是估算，不宣称数学硬上界。如现有组件拒绝新并行batch，协调原维护者 01a0a87f-f806-7883-9648-190e49447d86 作最小受审修复；不可绕过账本，辅助账号物理工作继续。
- API工程师辅助线程 01a0a948-10bb-7d03-8f1d-b1eeda7cb93c；其公开经验索引 `artifacts/R021/api-ground-002/coordination-public-index.json`、experience-candidates。只共享条件化控制/locomotion经验，不认为已验证完整行走。
- 框架辅助审查线程 01a0a94d-6143-74c0-80cd-03d0b61acaf0；`artifacts/architecture-review-20260916/memory-priority` 给长度与审计筛选组合候选。联系它让IKEA保持一致，修改只进自己的副本，绝不覆盖共享runner。

## 验收与产物

1. 立即写 state.json/STATUS.md，识别实际运行状态与下一步。只读确认列举交互候选，产出 inventory.json 与可读清单：视觉身份、来源节点、分离/可动部件、物理关节/碰撞/质量是否已证实、需适配项。没有读出的原物理标未知，禁止直接称可交互。不要先做UI或大框架。
2. 阅读GPT-as-Policy全部SKILL.md与.md文件，保存紧凑路径/用途清单；控制相关teacher_context/EEF contract/NOTES/history优先深入，网页样式/许可证等列明不适用即可，不要把全部文件当actor前缀。RoboRSI借鉴base/atomic/long_horizon、角色分离、task wiki、证据晋升。事件触发review，不每chunk多角色调用。
3. 校验目标门闭门reset、单位、轴向/铰链、门框净空、重力与碰撞。自主完成必要场景适配，不改源文件；宿主诊断与policy输入隔离。若锁舌/把手联动未建模，明确声明无锁舌变体；不能把纯推板成功叫解锁成功。仿真成立后尽快启动首个API策略真实回合，不一直准备。原API路径不能接入时先辅助账号策略实际推进并说明原因。
4. 每回合独立reset、唯一路径、唯一动作写入者/历史，冻结task/skill/controller/scene版本。成功至少是接触带动目标门显著开合、终态保持且机器人稳定；保留角度、保持时间等host审计，不把它们暴露给actor。终止分类区分物理失败、截断、提前结束、安全、系统。不要刚到门前就主动finish；持续尝试、单次失败不结束任务。失败/成功连续视频都保存，视频结束前不当可播放完成视频。
5. 主harness+skill长度每改检查831 words/6250 chars，旧版本保留。用适用条件/when_NOT_to_use/接口与版本/证据索引继承短skill。不要重做桌面十成功，不把静态预览或回放计分。人工反馈单列，H001004侧抓包络规则可作human_proposed迁移候选，顶抓不能套等高规则。
6. 与上述三个辅助线程持续交换证据提案，队列ACK/集成/验证分开；本地OUTBOX.md与inbox.md为桥梁，勿唤醒主账号桌面任务。接管后写ack.json给父会话，附自己thread与tmux名和实际后端。
7. 不停止：每个阶段自然结束前判断下一次物理试验，持续到任务链完成或真实外部阻塞。如需自然turn接续，允许本IKEA独立角色的唯一零模型接续器，严格只在该角色进程退出且turn.completed且新state=continue后resume同一辅助thread；不得复制/操作SIMPLE既有接续器、并发resume、自动重试usageLimitExceeded。不要创建Codex桌面主账号定时自动化。至少每60秒更新机器可读进度（等待推理可零模型读取状态），提供完成的视频链接，勿为更新而额外调用模型。必要时复用已有视频页，只能做小范围只读数据入口，不被UI分散。

当前父会话会核对启动、库存与首批物理证据。未完成不能标complete；真实技术阻塞写明尝试与可执行下一步，至少三次可比自主物理失败仍解不开才生成一个明确人工问题和连续视频。继续推进可独立工作，不按估计时间截断Astra。
