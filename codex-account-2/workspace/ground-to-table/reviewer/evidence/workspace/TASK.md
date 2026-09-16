# Second-account ground-to-table exploration

用户当前明确请求：读取 codex://threads/01a0a090-ddb2-73a3-9dd9-ce1a85f36f34，使用20x新账号探索，把原有红色物块从地上捡起后放到桌子上，需要有移动和操作，setting 与该任务相同。

你是负责实际推进的第二账号工程/探索 supervisor，固定 gpt-6-astra/xhigh。完成实施、物理试验、失败复盘与有依据的下一次迭代；不能仅提交计划或启动进程即退出。新的机器人 actor 及任何模型子进程一律经 /home/galbot/lizekai/RSI/codex-account-2/run.sh 启动。该账号后端已核验 planType=pro (20x)。无裸 codex/API 回退，不读 api.json/auth.json，不打印身份/令牌。收到 usageLimitExceeded 保存进度停止，不自动重置或循环创建空回合。

## Scope and source

先读取 /home/galbot/lizekai/RSI/AGENTS.md、ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md、本目录 SOURCE_THREAD.md。后两者中其他正在运行任务仅供协调，本进程唯一目标是地面红块放桌，不能改成 SIMPLE 苹果/门/箱子任务。三行决策规则继续执行：当前问题、总目标、不可重犯的错误。

来源 setting 是自由站立 G1 + 双 DEX3 + 原 model_38000 + RGB/合法本体观测 + 真实接触，实际原场景后端 MuJoCo；复用原机器人/红块/带腿桌子资产、动力学、50Hz tracker/250Hz PD和具名映射。最新延续路线为 UMI-4/现有固定 WristPI，详读当前合同并记录版本。只按本次任务需要把原红块初态放地上，选择足以要求真实全身移动的合理无碰撞初始布局；记录与桌面 seed 的全部差异，不改变质量/摩擦/桌高/机器人形态让任务变简单。不能声称原任务的桌面初态原本就是地面。不改原权重、环境或外部资产，不上真机。不要悄悄切成不同仿真/控制器。

## Isolation

其他第二账号 supervisor 正在更新共享 RSI。你只写本目录 /home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table 及其子目录。创建最小源码快照/独立 task adapter、自己的 memory、技能版本、状态文件、日志、视频和评测，manifest 记录复制时源文件哈希。公共 rsi/tools/skills/ITERATIONS.md 和其他 campaign 只读；如发现公共修复，写 patch 提案留待合并，不能就地改。复用已有只读 Python 环境 /home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python 及 locomanip/src，源资产保持绝对只读路径。检查复制源码中 ROOT/CODEX_LAUNCHER/数据路径，避免独立快照仍写公共目录。临时缓存设在本目录。不重复下载安装。

## Reuse and execution

优先读 tools/learn_grasp_skill.py、rsi/live.py、rsi/evaluator.py、rsi/skill_learning.py、rsi/codex_app_server.py、skills/loco-manip-direct/SKILL.md、skills/loco-manip-core/SKILL.md及当前参考合同。红块桌面抓取 R018 已有10次独立原生成功；可按现有授权检索自身公开观测/动作经验，不能把旧任务成绩或回放算新任务成功。公共 ITERATIONS.md 末尾已有多种脚点参考不抬脚的反例和 control-chain/IK诊断；选有区分力的新测试，不重复已否决的脚点平移。直接PD/不同模式/合成参考仅标记开发诊断，不能冒充正式四点 ScaleBFM 策略成功，也不能将隐藏状态或开发生成动作喂入视觉 actor。

建立物理可验证的独立评估：机器人通过自身腿脚产生有证据的水平位移/支撑变化，随后真实接触抓起原地面红块、离地运输、在原桌面释放，手离开后物块在桌面稳定保持且机器人未倒。验收数值选合理明确门槛，写入 manifest；区分每阶段达成与全流程成功。移动不得用腕位移、纯侧倾、物体推落、瞬移/设qpos/固定根/焊接方块替代。每个 episode 独立 reset；episode启动后的场景真值修改禁止。评估器可读取物体/接触真值用于审计，但 actor 仅获 RGB、标定、本体与公共三态回执，不获目标真值坐标/隐藏奖励。

先检查非法状态/虚假成功反例，再实现并验证评估；复用已有视频管线保存失败与成功（初态、脚部/全身移动、接触、终态）。动作到位超时、物理步预算、模型推理等待分别记录。Astra/xhigh完整等待，不按墙钟估计截断/重发；若物理等待期间暂停必须标注。技能学习与冻结测评分开；主 harness/skill 每次修订检查 <=831 words 且 <=6250 characters，保留原版与经验出处。一次失败继续有依据的探索；同一假设两次无新增信息换诊断。

## Persistence and handoff

所有预计超过60秒的子任务用 tmux + tee，唯一带日期会话名，不依附SSH/当前执行会话。当前 supervisor 已在 tmux 中。先在本目录 STATUS.md 写计划/当前阶段，之后每次实质进展更新，并维护 machine-readable status.json（backend、account_route、model、setting_manifest、attempts、phase_results、overall_success、latest_video、blocker、next_step、running_sessions）。记录每轮失败原因/证据/下一假设，不能无解释反复重试。

账号验证记录 app-server initialize 的 codexHome 与 thread/start 的 model/effort，不输出身份字段，所有新模型调用都第二账号。完成后输出事实结果和可点击证据；若暂不能成功，保留持续运行的有效任务，并写明真实瓶颈与下一实验。只有必须用户澄清/授权或配额耗尽时才停止；不要因缺示范、首轮失败或需要写仿真代码而停。
