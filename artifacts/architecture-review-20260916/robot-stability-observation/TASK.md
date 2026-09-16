当前问题：SIMPLE XMovePick1完整回合在机器人倾角25.070885度时触发保护停止；策略公开复盘无法直接观察精确原因。总目标：最小补足合法机器人本体反馈以服务后续任务学习。不可重犯：不得向actor送入物体/接触/奖励/host审计真值，不改控制器、安全阈值、在线文件和在途回合。

你是现有辅助架构审查者，不新建角色/子代理/平台，不调用模型/API/仿真，不使用主账号。固定当前第二账号Astra/xhigh。主任务为这一个有边界的候选交付；队列里的Handover等其他检查本轮暂不扩入，也不重复已完成NT/长度研究。完整等待自己的推理和工具，不设置推理超时。

先读 artifacts/R019/recovery-20260916/robot-stability-observation-question.json 与 robot-stability-framework-message.txt。这是host-only工程证据，绝不转录到actor公开包。只读当前rsi/live.py、rsi/policy_harness.py及其直接关联定义/现有回归。参考第一优先级ref/GPT-as-Policy的公开机器人反馈与短skill思路，利用已完成REVIEW.md引用，避免重复大搜索。

只在本目录写candidate/、最小patch、测试、证据和报告；备份源码hash。禁止修改在线rsi/、tools/、skills/、任何campaign，禁止启动/重置/打断物理或模型。SIMPLE唯一publisher自然回合边界实施，候选不自动部署。

先验证缺口与红灯复现，再做最小候选：命名机器人本体root高度、倾角、必要姿态和同源实际采样趋势进入公开observe与robot_motion摘要。只新增必要字段，不新通用schema平台；已有等价字段就复用。严格核对安全判断到底使用哪个命名body/root坐标、单位、参考轴，字段与其保持同一语义；不得按joint位置猜robot/object自由关节、不得照搬Isaac交错序。若阈值和本体状态来源不等价，清楚说明差异，不伪造margin或重定义安全。保留采样sim时间与同回合身份，首次/缺失/非有限值不要补零或跨reset差分。趋势从真实已记录采样推导，不能凭synthetic轨迹声称物理改善。可公开既有安全阈值及同义margin，仅在有明确同源依据时加入，绝不改变阈值与动作限制。

验证应有：当前缺字段红灯；同名本体有非单位姿态/根高度的语义检查；pose坐标/四元数约定和tilt与原安全判据一致；命名映射能排除先出现的物体freejoint；reset/首次样本处理；公开payload递归允许字段和poison object/contact/reward/evaluator sentinel泄漏测试；原普通observations/motion回归适量执行。可以读取已有公开机器人轨迹做一致性检查，但不启动新物理、不读取凭据、不发模型/API请求。若增加runtime/skill文字，校验831words/6250chars/5357非空白并保留版本；优先不改skill，不能静默截断。

到交付时对在线文件新hash做漂移检查；有无关并发变更不要覆盖，可在最新副本重基最小patch并重跑受影响检查。结果明确candidate_only，机器人本体状态可见性改善不证明防止失败/泛化，不晋升共享core。通过后用codex-account-2/run.sh queue向唯一SIMPLE publisher 01a0a867-d7aa-71f2-8547-e264d6d09ede 发一次工程候选交接，显式openai/gpt-6-astra/xhigh，保存回执，排队不算ACK。不得send_message_to_thread唤醒桌面主账号。

过程写简短progress.json；最后留FINAL.md、result.json、补丁/哈希、测试证据、明确部署边界与限制，然后结束此有限工程turn。不要等待全部机器人目标完成。
