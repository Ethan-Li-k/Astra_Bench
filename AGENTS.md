# RSI 工作约束（2026-09-15）

- **最新稳定性与冻结验收**：按 `ref/USER_UPDATE_20260916_SIX_TASK_FOCUS.md` 的 SIX-TASK-FIVE-STABLE-V1，每项固定完整候选连续5次独立审计成功后，另做预登记10回合冻结测评。旧在途不倒签；改skill/可读经验/控制/资产/反馈即新候选归零。冻结建议隔离保存，不进入下一回合加载；先测试非法版本/入口/重复reset/新增经验，再放行。
- **最新范围优先**：先读 `ref/USER_UPDATE_20260916_SIX_TASK_FOCUS.md`。暂停 IKEA 与地面搬运，SIMPLE 本阶段只调度 XMovePick、BendPick、Handover、Mobile P&P、Grasp、XMoveBendPick；保留旧91入口库存但不扩张。已授权六类在途完整收尾，非六类收尾后不续开；精确入口以原README六项表为准，Grasp=TabletopGraspMP、BendPick=BendPickMP、Mobile P&P=LocomotionPickBetweenTablesTeleop；MP待控制适配，禁止近似变体抵分。历史成功与当前六类新测评分开。
- **人工求助与视频**：按 `ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md` 最新补充，仅同任务/同阶段、可比机制和控制合同的同种可观察失败，至少3个独立真实attempt/reset且自主修改仍未解决后，才考虑代表性求助；不得合并不同苹果失败或跨推门/抓取凑数。所有失败照常记录/修订，主动视频不受求助门槛限制。唯一API校准实际3.39 RMB，结算由协作API分支负责，不重复记账或查询费用。

- 用户已授权在本项目编写代码和运行仿真；暂不上真机。
- 可以新建独立环境，但不得覆盖、修改或破坏任何既有环境，尤其是 `psi_deploy` 和 `.venv-psi`。
- 本任务新增代码、环境、缓存、模型、日志、录像和评测文件统一放在 `/home/galbot/lizekai/RSI`。既有外部资产仅只读引用。此项覆盖旧的大文件存储位置要求。
- 当前进入无人工示教的 Direct 技能学习：允许从自己真实尝试的轨迹中提炼经验、跨尝试读取经验并修改 skill；冻结测评另行隔离。没有 π0.5 或外部成功示范前置要求。
- 始终使用 `gpt-6-astra`、`xhigh`；禁止自动降级模型或推理档位。累计完成 10 次独立重置后的真实物理抓取，再进入 SIMPLE 场景继续工作。
- loco-manip 主 harness/skill 不超过本地 `GPT-as-Policy` 最大 SKILL.md 的 831 words / 6250 characters；自动修改也必须检查上限，并保留旧版本、经验来源和失败记录。
- 必须保存失败和成功的录像及评测。优先 Isaac；未在 Isaac 执行的结果必须标明实际后端。
- 非必要不用额外计费 API；必要模型实验使用已有 Codex 套餐登录，不读取本目录 `api.json`。
- SIMPLE 复用 5090／ds4090 已配置的运行与视频管线，不重复下载或安装。远端已有目录为 `ds4090:/home/lidanshi/lizekai/SIMPLE`。
- Astra/xhigh 推理必须完整等待，不按估计的 chunk 延迟截断或重发；显式区分推理等待、动作到位超时和物理回合预算。同步暂停物理的诊断不得声称实时闭环。
- 长任务沿用全局 tmux + tee 规则；任何决策前写当前问题、总目标、不可重犯的错误。
- 10 次抓取之后，SIMPLE 推门至少成功 10 次；SIMPLE 所有可用操作任务各至少成功 1 次。按任务分别记录独立重置成功、终态保持、失败原因和视频；旧策略成绩与回放不计入。
- 套餐 `usageLimitExceeded` 必须停止自动重试并保留进度；不能按 30 秒循环创建无物理执行的新回合，不自动消费重置券。
- 后续新建的技能学习模型进程使用用户指定的 `codex-account-2/run.sh`，由其固定第二账号 `CODEX_HOME` 并清除主账号/API 认证覆盖变量；仍固定 `gpt-6-astra/xhigh`。正在运行的主账号回合等待完整结束，不热切换。启动器不可用时停止并记录，不回退到裸 `codex` 或 API。
- 每次新任务/回合前读取 `ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md`：尽量不消耗主账号；SIMPLE推门3次独立审计成功后才启动IKEA棕色卧室门的API探索分支；支持独立环境并行，按任务机制共享控制与locomotion经验。API预算已授权：累计每1500元汇报、全任务并行调用合计硬上限10000元，以 `ref/tasks/api-budget.json` 为准；付费前核实来源/计费并验证共享费用预留，不超额、不因汇报自动追加额度。
- 最新用户要求另见 `ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md`：已授权现在使用API推进并行与人工反馈学习，覆盖旧的全面禁止API条款；来源、定价和共享硬上限核实前不发请求，IKEA门槛是否取消尚待用户回答。用户辅助读图/空间判断/规划，agent负责具体标注问题、同信息证据包、失败复现及纠正验证；人工反馈回合单列，不混称无辅助Direct。
