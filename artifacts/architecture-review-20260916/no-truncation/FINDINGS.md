# 有界连续性审查

本轮有证据的重大中断是**主机重启及其前的网络断线通知**，不是简单的统一 900 秒推理超时。用户报告的严重截断成立为需调查的现象；不能用已经修过 timer 否认它，也不能把所有结束都归给 timer。

[本轮原回执分类](evidence/outcomes.json) 固定快照，未重新统计历史成功。SIMPLE 苹果0007、放盒0003、水龙头0007分别122/52/61动作，约240秒物理预算；模型 turn 正常 completed，物理任务仍未完成。这些是预算结束而非自然推理被取消。`finish_attempt` 已只记录 stall 并返回当前观测，`tools/learn_grasp_skill.py:131` 的行为本次保留。

门0015：1次 turn/started、86次 tool call、5条 network error、0次 turn/completed。错误含 responseStreamDisconnected、websocket premature closure 和 SSE idle timeout；服务端/传输 idle timeout 不等同本地900秒计时器。门 reset boot ID 与当前 boot ID 不同，IKEA重启 incident 也独立记录重启。08:58 PROGRESS 的 running 已是旧快照，不应继续显示在途推理。没有确认旧远端 turn 终态，不能并发恢复、更不能重放动作61。新候选只覆盖**匹配的已结束网络 turn**，不冒充解决此旧回合。

API-ground：最新恢复 owner 明确 `host_reboot_infrastructure_interruption`、`inference_in_flight=false`。54完成调用、23动作/108.98秒是重启前公开计数；回执55为空、最后动作部分证据受损、视频未封口，不能作为完整审计动作分母或成功。核看53/54完整回执，均 completed；55远端结果/费用未知，绝不自动重发。现有 max_output_tokens=16384 是请求合同，不能据它推断53/54达到上限；本次未找到模型 incomplete/output-cap 触发的实证，不能把代码潜在可能写成实际根因。API HTTP 本来 timeout=None；actor.py:82 区分 response.completed/failed/incomplete，未完成会退出而非安全重发。

IKEA：快照 actor_running=false、physical_attempts=0、audited_successes=0；重启后 owner 进行场景/机制诊断，不属于“actor推理还在等”或一次门操作成功。新 scene 细节属于 host 工程证据，没有带入 actor 经验正文。

## 代码与第一参考

- 原 `rsi/codex_app_server.py:149` 已 `next_message(None)`；`tools/learn_grasp_skill.py:308` 已循环普通 turn；不重复宣称修复。
- 原 adapter `:93` 的 turn/start ACK 仍用 self.timeout，且异常后没有提交锁；`:164` 匹配失败 turn 直接 raise，caller `:318` 清理 host。离线原版复现为4个失败断言+1个错误，其余5个边界通过。候选改变这些代码路径，不将近期网络通知伪造成已存在的失败终态。
- 采用第一参考 `ref/GPT-as-Policy/.../skill/run.py:211` 同 thread/rollout、保留动作、携带进展的思想，及 `network_recovery.py:19` 必须确认闭合的原则；保留更保守的缺失信息拒绝恢复。**不照搬** `run.py:256` deadline、`:365` 两次普通 continuation 或 `network_recovery.py:4` 固定重试序列。
- `.../skill/transport.py:78` 与 RSI `rsi/stdio_transport.py:79` 的请求响应/EOF分离说明 None 等待不会隐藏真正 EOF；不新增 watcher/重连服务。
- GPT-only `SKILL.md`、`context/teacher_context.md`、`context/eef_control.md` 用于短入口、持久 NOTES、任务知识/控制合同分离。未复制其 ARX 关节/EEF偏移、夹爪方向或数值世界轨迹。RoboRSI 只复用首轮条件前提/职责分离结论，不再通览。

所有精确源路径及hash见 [source-manifest.json](source-manifest.json)，代码基线另见 [snapshot-manifest.json](snapshot-manifest.json)。物理条件经验复用首轮已经审阅的公开轨迹，见 [public-sources.json](skills/public-sources.json)；没有新观察就不编造新成功或泛化收益。
