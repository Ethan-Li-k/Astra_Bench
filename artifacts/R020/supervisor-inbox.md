# R020 用户要求交接（预算/ACK 已更新）

## GROUND-REBOOT-RECOVERY-20260916：新辅助owner ACK

当前问题：主机重启中断api-ground-002/episode-0002，旧owner消失。总目标：原桌位红块接近→抓持→持物移动→桌面放置，保留独立重置与证据。不可重犯：不重发结果未知的call55、不把23动作当三次失败、不迁移未经审计的成功、不唤醒主账号。

新唯一辅助owner `01a0a982-cec5-71c0-b771-091c31df61f2` 已消费本inbox旧的API/框架/UI交接与最新NO-TRUNCATION指令。旧owner `01a0a948-10bb-7d03-8f1d-b1eeda7cb93c`不再是反馈入口。公开恢复字段见 `api-ground-to-table/recovery-20260916/progress.json`；54完成调用、23动作/108.98秒是最后公开计数，动作23只有命名观测中的ACK仍在，独立执行/RGB证据损坏。无完整状态可同回合恢复，MuJoCo基础设施中断，不计人工求助失败。向框架owner的恢复交接 `api-ground-to-table/recovery-20260916/handoff-framework.txt` SHA256 `99c904f7efd0cb89b30b6da92c2248a56add433080a47ccd30dff971faaafc98` 已queue；未声称集成。请在下一个自然边界提供controller/contract兼容的公开locomotion候选及反例；本分支不修改shared core、不复制世界目标。

2026-09-16 修正：旧版“预算待答复、ACK未到”已被新事实取代；原文与当时回执保存在 R020/history 的标注历史快照中。本文件是已交付要求的当前记录，不要求再次发消息/再次确认。

主控 thread：01a0a867-d7aa-71f2-8547-e264d6d09ede。已有公开日志真实确认：

> R020-PARALLEL-SKILLS-20260916 ACK — 已读新增要求及预算文件；IKEA 须满足 3 次独立完整 host 审计成功且 API 配置明确，当前不启动。

证据：delivery-state.json、ack-verification.json，含原始公开日志字节偏移与事件哈希；queue-receipt.txt 单独只是入队回执。

主攻 SIMPLE 推门（总目标10次），其余任务独立并行；推门3次独立重置、完整回合、真实 host 审计成功后，再并行 IKEA 右侧棕色卧室门，SIMPLE继续。当前推门0/3，locomotion未验证，不启动IKEA探索。所有正式成绩仍需用户指定接口，不计诊断、回放或自述成功。

API预算已经明确授权：所有角色/环境/分支累计合计不超过10000元，每累计1500元向用户汇报，汇报不追加或重置预算。唯一授权源 ref/tasks/api-budget.json。API来源、模型价格、计费币种/换算依据和实际限额接口仍未核实，当前付费调用0；不读取api.json/auth.json、不猜来源、不重新询问预算。缺来源只阻塞付费调用，不阻塞SIMPLE。

SIMPLE supervisor 是 skills/loco-manip-core/SKILL.md 唯一发布者。ground-to-table 由其独立thread在 codex-account-2/workspace/ground-to-table 写域维护；只交换有证据和版本的候选。直接复用 ref/ACCOUNT2_ROLE_SKILL_REVIEW.md，不重复研究角色架构。

本辅助线程独占 tools/coordination 与对应 R020 维护；共享账本和门槛只有离线校验/登记功能，不发请求、不启动环境。rsi-r020-coordination-wait 仅检查门槛/预算状态和ACK。主控自然结束接续已由 rsi-simple-continuation-0916 / codex-account-2/continuation/watch.py 负责；不建立其他resume watcher，不并发resume，不修改主控runner/控制器。


## ARCH-REVIEW-20260916-V1（只追加，下一自然边界）

辅助账号架构评审已交付：/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916/HANDOFF-SIMPLE.md 。08:28UTC快照桌面10、门5、抓盒1；候选只修skill+runtime总长检查，8项离线回归通过，未部署/未物理验证。保留已有提前结束、异常与placement改动。请先保留并压缩各任务入口再考虑合入，勿打断在途回合。API交接文件HANDOFF-API.md仅待owner转交。此追加只算queued；ACK和集成需主管另行明确。


## ARCH-MEMORY-PRIORITY-20260916-V1（候选未合并，下一自然边界）

第二项有界修复已交付：/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916/memory-priority/FINAL.md 。真实放盒0001审计否决置顶问题已复现；现有success_review→episode_status经两个runner接入，每次检索更新资格，不回写经验、不暴露host载荷。18项检索回归及组合后的原8项长度回归通过；独立/组合补丁择一，勿重复叠加。第一轮协调者ACK按父任务转述记录，非部署证据；本条仅queued，待主管逐项ACK。当前相关live hash与快照一致，未改在线文件或运行物理/API。固定合同/控制器/reset验收及公共反例见INTEGRATION.md；勿打断在途回合。

## UI-PROGRESS-20260916-V1（公开经验协作请求，仅追加）

用户最新持续方向见 /home/galbot/lizekai/RSI/api-ground-to-table/CONTINUATION-20260916.md。API owner 01a0a948-10bb-7d03-8f1d-b1eeda7cb93c 继续原桌位地面红块：接近→站稳可抓→抓持保持→持物移动→桌面释放/退手/保持。请 SIMPLE owner 在下一自然边界提供经审查的控制、locomotion、站位和持物移动候选，列 task/controller/contract hash、公开轨迹/成功或反例、前置条件和不适用项；无兼容证据请明确不迁移，不复制世界坐标或隐藏物体真值。优先本地 GPT-as-Policy，次参考 ref/RoboRSI；沿用唯一共享 skill 发布者，不要求暂停 SIMPLE、改变其任务或预算。

现有 UI http://127.0.0.1:8765/#api-ground-progress 已新增只读 API 区，公开源为 actor-adapter/auxiliary-progress.json、对应 result.json 和存在的 public_history_index.json；首批 6 API/3动作是预算截断未完成，抓取/搬运/放置未验证；录像完成且 ffprobe 可读才发布。20 项 UI 后端回归通过，仅重启已确认的 rsi-human-feedback-h001 服务，其余机器人进程未动。三方交接证据 api-ground-to-table/progress-ui-verification/；本条只是 queued，待逐项 ACK，不称集成/物理验证，不为消费消息中断或并发 resume。


## IKEA专属分支接管通知 2026-09-16
当前问题：用户已为IKEA开新专属协调会话，明确现在探索棕色卧室门。总目标：门→苹果→冰箱→放入，复用你方证据。不可重犯的错误：不唤醒主账号、不打断在途、不共享隐藏真值。最新授权/边界请读 /home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_IKEA_OWNER.md；本分支辅助工程师已在 rsi-ikea-engineer-0916 启动，独占 ikea/。请向 ikea/inbox.md 追加ACK/公开经验路径；入队不等于已集成。 请保留SIMPLE主线与shared core唯一发布权，将IKEA独立探索交由此分支；R023/工具只读复用，不再重复建同目标IKEA actor。若你方适配已在进行，请说明已有写域/进程供安全接续。请提供成功推门skill/抓盒skill与合同/版本，host审计仅用于验证不输入actor。


## GROUND-003-REVIEW-20260916（新证据；下一自然边界）
GROUND-003-REVIEW-20260916：当前问题：002同boot基础设施中断已保留；003新reset真实安全停止已复盘。总目标：原桌位红块走近抓持携物放桌，网页持续进度。不可重犯：不重发002未知55、不把安全停止当三次失败、不迁移坐标/隐藏真值。
当前唯一辅助owner 01a0a982-cec5-71c0-b771-091c31df61f2。公开review路径 api-ground-to-table/recovery-20260916/episode003-review/review.json SHA256 640b2c46937be5778581207a4d84d42a05a27f14346aacf5b3d8f341487f35b4。003为MuJoCo，10调用/5动作/18.0物理秒；倾角15.819→25.005°历时0.44秒，高度0.76562米。前一target_reached末三个倾角15.653/15.730/15.819正在上升；最终右脚升高<1毫米。这只支持‘到位不等于站稳’反例，腕/脚/姿态耦合原因尚未分离。完整18.04秒视频 /videos/api-ground-episode-0003.mp4 已网页发现；视频含诊断视角，policy经验仅原始相机/命名状态/ACK。
004已独立reset，检验降低落脚终点需求与后续稳定趋势，artifacts/R021/api-ground-004/public-transfer.json有固定合同hash和选/拒原子经验。读取SIMPLE door0014撤手重居中与boxplace003不充分跟踪，只迁移条件化检验方法，不抄坐标或宣称空手=持物。ACK框架HANDOFF-API/memory-priority/NT-v1：长度/资格/连续性原则已局部采用，CodexRPC网络补丁不适用直接Responses API，无shared core覆盖。唯一本分支持久监督rsi-ground-continuation-0916等待当前工程turn与actor自然结束后同辅助owner接续。此消息仅新证据交接；queued不代表对方ACK/集成，不要求停其他任务。


## GROUND-004-REVIEW-20260916（公开新反例；下一自然边界）
GROUND-004-REVIEW-20260916：当前问题：004已按真实传输边界结束，42完整API调用、43结果未知，19动作/83.04物理秒。总目标：原桌位地面红块走近抓持携物放桌。不可重犯：不重发004未知43/002未知55，不把同回合15次停步或传输中断算三独立物理失败。
唯一辅助owner 01a0a982-cec5-71c0-b771-091c31df61f2。公开review api-ground-to-table/recovery-20260916/episode004-review/review.json SHA256 0709753a0c94ba639acf23ae8e26007cadbbd0ceb2f12058d65a77ca2be339a2。原result/video/ACK未改；83.08秒完整录像网页 /videos/api-ground-episode-0004.mp4。前三次实际移足分别118/101/131mm，峰值升高39/44/42mm；足部相向偏航累积，后15种姿态/方向/时序/roll检验未带来新移足，低倾角与腕回撤不足以证明步态恢复。只迁移有前提的空手反例，不分享坐标或host接触真值。
005已通过独立batch/auth及正常执行审批，检验早期抬脚阶段方向保持；所有未知hold原样占额，新reset不是43的恢复/重试。shared库9008e224...已在本分支schema2实际接入，明确ACK见同目录IKEA-BUDGET-PARALLEL-V1-ACK.json，库发布与真实API验证分开。传输新增内容无关元数据诊断stream_evidence.py，仅事件计数/字节/HTTP/终态标志；None推理deadline、零重试，不能追溯断言004远端已结束。44项独立边界回归通过，原共享core/publisher未改。已有唯一watcher PID456959接续同一辅助owner；不要求其它分支停进程。此次queue/inbox不冒称对方ACK/集成。


## GROUND-005-HTTP429-20260916（新系统边界与公开反例）
GROUND-005-HTTP429-20260916：当前问题：独立005已结束，9调用完成、第10请求HTTP429，4动作/20.04秒；当前actor已退出，自动接续暂停。总目标：原桌位红块走近抓持携物放桌。不可重犯：不重发002/55、004/43、005/10，不用新batch或账号绕过429、不把系统中断算物理失败。
唯一辅助owner仍为01a0a982-cec5-71c0-b771-091c31df61f2；现有唯一watcher456959存活，本owner已写blocked。原结果/回执保持，三笔未知hold继续完整占用，不查询quota/费率；HTTP429子码/正文未记录，不能断言是额度或限流。无006。005完整真实录像20.08秒网页/videos/api-ground-episode-0005.mp4，Range206已核验。新公开review api-ground-to-table/recovery-20260916/episode005-review/review.json SHA256 fd1aab2ea59367a490bc125ca7793c8e727e0d28803cb1d732137a8f86f4c95a。
动作2/3/4实际左/右/左踝推进165/152/140mm，但最后右支撑足后退32mm；方向较004小有多条件混杂，后段尚未检验，不能晋升步态。条件化候选见同目录experience-v005.json，未改shared publisher或运行控制器。SIMPLE门19/boxplace4最新公开记忆已留作下一安全边界审阅，不追认005已使用。只交接新系统边界和公共反例，不要求其它分支停止/修改任务，不唤醒主账号。排队不是ACK或集成。
