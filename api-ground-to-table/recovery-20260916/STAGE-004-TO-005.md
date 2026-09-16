当前问题：004因API流缺少终态事件中断并已复盘；005新的独立物理尝试正在推进，尚未抓持。
总目标：原桌位地面红块走近→站稳可抓→抓持保持→携物移动→桌面释放/退手/保持，网页真实进度和完整录像。
不可重犯的错误：不重发002未知55或004未知43，不放宽安全线，不将同一回合多动作算多个独立失败，不留下无监督actor。

004真实结果是MuJoCo基础设施/传输中断，42调用完成、43结果未知、19动作、83.04秒物理；native in_progress，没有安全或物理预算终止。原43约610.59秒后流结束但没有终态事件，原transport没有事件统计，不能断言远端是否完成或具体网络根因。原sim已关闭且没有完整状态checkpoint，不恢复旧reset。原result/receipt/ledger不回写，002/55与004/43各1217分未知预留仍完整占用；completion文件名不等于完成状态。[追加复盘](episode004-review/REVIEW.md)、[公开源和统计](episode004-review/review.json)、[独立系统审计](episode004-review/host-integrity.json)。

[004完整录像](http://127.0.0.1:8765/videos/api-ground-episode-0004.mp4) 为83.08秒、H264、1280×544、4919969字节；只读ffprobe通过，网页Range返回206。它包含外部诊断视角，policy经验仅使用原始头/腕相机、命名机器人状态、目标/ACK；关键原图副本和哈希在episode004-review/keyframes。旧002损坏录像仍独立保留。

物理反例：动作2/3/4实际左/右/左踝推进约118/101/131毫米，峰值升高39/44/42毫米；足部相向偏航同时增大。之后15动作改变支撑/姿态/方向/时序，仍未形成新脚位移动；全回合公开倾角峰值低于14.4度。低倾角和手回撤都不足以证明步行恢复；不能将近桌面画面推断为接触真值或控制器故障。下一假设是提前在可见抬脚阶段保持/纠正方向，避免累积到落地停滞后才纠偏。若方向约束阻止清脚或保持方向仍停步，则该假设被反驳。仍是空手候选，不代表已掌握步态或携物移动。

005已经独立授权并通过正常工具执行审批，以直接API gpt-6-astra/xhigh运行。reset UUID `48ca5927-1f1c-42d6-be67-7db1ba5149c1`，new_model_and_data_instance=true；原G1/DEX3/model38000/WristPI/table0、25度/0.55米安全线、成功定义均未变。单批120调用/180物理秒，原共享预算及实际费用报告边界不变。新005不是43的恢复或重试，旧payload/ID未复用。[批次登记](../../artifacts/R021/api-ground-005/registration.json)、[独立授权](../actor-adapter/authorization-005.json)、[启动回执](episode005-preparation/launch-receipt.json)。

005主skill+runtime为769词/5934字符/5154非空白字符，均合格。GPT-as-Policy短合同/观察执行验收为第一参考，已有RoboRSI条件化生命周期评审第二；新公开反例、前提、拒用范围和版本见 [public-transfer](../../artifacts/R021/api-ground-005/public-transfer.json)。框架四份已消费候选哈希未变，不覆盖shared core。005启动后读到SIMPLE较新的door0019、boxplace0004公开候选，单独留作下一自然边界审阅，不追认005已使用、不热更新、不按native标签推广成功。

传输仅增加内容无关诊断：HTTP状态、白名单事件计数、字节数、DONE/终态/EOF标志和接收时长；不保存正文/私有推理，不设置推理deadline或重试。完整等待与自然无工具completed turn同reset接续保持。已按 [OpenAI streaming事件文档](https://developers.openai.com/api/docs/guides/streaming-responses)区分语义终态和数据片段。005首个真实回执已有response.completed与DONE/EOF，HTTP200、返回Astra/xhigh；这验证新记录路径，不证明004远端问题已修复。新增api_requests_started/api_calls_completed分列，未知请求不再被公共计数误称完成。

28项actor回归、12项授权/未知hold/连续性测试、4项流诊断测试，共44项离线测试通过；skill-creator校验通过。初始缺模块复现、错误测试顺序以及其它合法分支并发写账本导致的测试夹具误判均保留日志。最终测试约束所有写入在合成目录，允许其它分支正常追加生产账本，逐行确认原ground请求未变。没有环境安装或修改。

最新宿主核验：005 actor PID **807365** 存活，tmux `rsi-api-ground-005-0916`；既有唯一监督 PID **456959** 存活并持有owner.lock，tmux `rsi-ground-continuation-0916`。唯一owner为辅助 `01a0a982-cec5-71c0-b771-091c31df61f2`，监督已实际在004 actor退出、上一工程turn完成后接续本turn，未并发resume。当前owner-state绑定新的005及本次日志，写入时间晚于本turn启动；下一个边界是本工程turn/进程与005 actor均自然结束后的公开复盘，再按真实授权准备独立尝试。[核验快照](episode005-preparation/live-verification.json)、[监督绑定](supervision/owner-state.json)。当前没有已知新执行阻塞，旧两笔请求仍未决；未来额度/权限/预算/系统边界不能自动重试。

核验时005已有8次完成调用、4动作、20.04秒物理，仍未抓持。后续以 [网页](http://127.0.0.1:8765/) 及actor-adapter/auxiliary-progress.json为准，管理更新时间不充当新物理进展。

预算库 `IKEA-BUDGET-PARALLEL-V1` 的明确接入ACK见 [BUDGET-ACK-005.json](BUDGET-ACK-005.json)，区分共享库发布、本地注册/离线验证与真实API回执；原共享库sha9008e224…未改。新公开证据已一次queue框架辅助并追加SIMPLE既有inbox，不声称对方已消费/集成。网页仅写本owner工程ACK，无新人工回答或伪造反馈验证。上一RESULT.md未覆盖，本阶段追加到CONTINUATION-RESULT.md。

最终公开快照：9完成调用，4动作，20.04物理秒，ended；源文件时间保持，详见episode005-preparation/final-public-snapshot.json。

005最终复盘与阻塞：原日志已明确第10请求HTTP429，不能再沿用上文“actor存活/无已知阻塞”快照。原actor已退出；9调用完成、4动作/20.04秒物理，20.08秒完整视频已封口并网页Range206验证。HTTP429子码未知，不查询quota/费率，不准备006或自动重试探测。002/55、004/43、005/10未知hold保持。最终公开反例、四动作统计、原图、原证据清单及本地账本完整性在[episode005-review](episode005-review/FINAL.md)，没有回写原result或热改原控制器/监督。

现有唯一watcher456959仍存活并持锁，owner-state已更新blocked，绑定本turn精确日志与episode-0005。当前工程turn退出后它将保持阻塞，不继续自动发模型请求。真正恢复条件是网关限制解除的可核验证据和安全边界，而非追加预算或更换账号。具体交接与网页状态见[CONTINUATION-RESULT.md](CONTINUATION-RESULT.md)和[005复盘](episode005-review/REVIEW.md)。
