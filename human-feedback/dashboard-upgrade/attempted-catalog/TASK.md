# 已尝试任务清单与NT正式发布状态：小范围维护
当前问题：实际已尝试的新垃圾桶/椅子/XMoveBendPick不在固定6项列表；NT-AUDIT已发布并由门19加载，旧候选提示已过时。
总目标：用既有受限来源自动展示实际尝试任务，准确区分发布、加载及真实断线恢复验证。避免以后每加任务都开一轮UI改码。
不可重犯的错误：不改actor或技能；不截断推理、不制造断线、不发模型/API/物理实验；仍由原唯一辅助网页工程师串行发布。

你上一轮已完整结束。只改现有human-feedback UI/tools必要部分，回执/备份在本目录。无需重设计、安装或全量回归。已知确切来源：
- artifacts/R019/campaign_audit.json：当前新增trashcan-campaign、chair-campaign、xmovebendpick-campaign均physical_attempts>0，task字段是真实注册任务名；苹果审计现已1，计数只读来源不要手改。
- artifacts/R019/nt-audit-integration-20260916/status.json：发布者63测试、after文件哈希、自然边界door18→19、physical_network_recovery_verified=false。
- artifacts/R019/door-campaign/episode-0019/policy_instruction_budget.json：network_continuation预留与新合同实际加载证据，门19尚在途，不宣称完整回合成功。
- artifacts/R019/recovery-20260916/permission-contract-fix.json及permission-physical-route-verification.json：现status=published_and_verified_on_formal_physical_actions，不能再仅说下一reset待生效。
- 原instruction-cap-integration/status.json和reviewer候选结果保留历史，不修改它们伪造新状态。

任务清单：保留现有6项ID/顺序/链接，随后从campaign_audit中的已实际尝试campaign发现新项。只接受RSI/artifacts/R019的直接子目录、严格*-campaign basename、canonical路径/无symlink/不能dotdot/外部路径；任务须是源中声明的SIMPLE注册task，且有可核验physical_attempt/action evidence，预检、空reset、未尝试不显示为物理任务。重用当前结果/原始图/封口视频/审计门槛逻辑，不用任意路径，不新增注册平台。动态任务也要接入case_media同回合绑定，不能仅展示卡片却无法引用其合格证据。现有中文名称保留，可给已观察新任务简短中文名；以后未知名字诚实显示注册名。未知计数≠0，结果封口优先残留等待标记。只读清单不得执行任何来源字符串。

框架：新的明确publisher NT-AUDIT发布回执优先于旧候选和旧部分上线字符串。显示“续接审计已发布；门19已加载；真实断线恢复尚未验证”，权限真实动作验证单列。保留63离线测试≠真实网络收益、不热改在途/shared core未晋升等边界。当前状态字面值published_tests_passed_pending_formal_boundary与门19budget共同说明发布/加载，不能误称已完成真实恢复验证。若后续明确回执更新，用其字段更新；不从回合成功或视频播放推断network recovery。

验收：定向fixture覆盖3个新任务发现、未尝试不进入、非法/外部/symlink路径拒绝、媒体仍绑定本回合、已有6项顺序与计分不变；NT旧候选+新发布优先级、发布≠加载≠真实恢复验证、权限状态。仅身份核实后重启网页；实际8765检查新任务及至少一段可播放新录像、framework文字，截图和回执。测试答案绝不投生产。仅向原SIMPLE辅助owner发一次工程交接。完成这项维护后结束，不等待机器人完成全部任务，也不额外开模型试验。
