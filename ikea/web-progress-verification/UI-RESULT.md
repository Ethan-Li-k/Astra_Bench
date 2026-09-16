# IKEA 网页增量：候选已交唯一 UI owner，尚未上线

目标入口：http://127.0.0.1:8765/#ikea-progress；目标只读路由 `/api/ikea-progress`。**本分支未将候选发布到在线站点，不能把目标 URL 当作已验收的新功能。**

本轮核实发现 `rsi-dashboard-upgrade-0916` 同时持有 human-feedback/ui 与 tools 的发布权，且已开始重写首页，打开其用户授权的反馈功能。原用户要求“如其他写者冲突，只提交候选给其 owner”适用：本分支只在 `ikea/web-progress-verification/` 写候选、测试和证据，未改 live ui/tools，未重启 UI，未控制任何其他进程。现服务核验时为重启后的 PID 59551/pane 59549，不使用旧 PID。

候选提供 IKEA 状态适配、区块和 10 秒刷新脚本，见 [INTEGRATION.md](INTEGRATION.md)、candidate/ikea_progress.py、candidate/ikea-section.html、candidate/ikea-ui.js。适配精确精选字段，兼容工程师实际 `schema:1`、建议 `schema_version:1`、旧 state、heartbeat、incident 与 recovery ACK；最后实际进展、心跳、页面获取时间分开。旧 API 的推理状态提供重启后“最后已知”标注函数，不改原终态分类。抓门/苹果/冰箱/放入均未验证，缺字段未知不编零。普通页面不显示私有绝对路径或 host 载荷。

已读取的新公开状态：MuJoCo FBX-derived no-latch v1，源资产物理核对完成、派生场景对齐准备；0 策略尝试、0 审计成功；工程诊断 1 次/6 模拟秒，不能计作策略成绩。原始工程说明不直接送浏览器。此为证据快照，不是实时进程运行保证。

真实诊断录像已通过独立读取核验：`ikea/diagnostics/door-v1-001/video/episode.mp4`，6.04 秒，SHA256 `3f68a2e41ff51f02452ad0448f6e05f784072936d181c21aaeefd2978c4246b2`。只读核对 validate_door.py 的逐物理 tick 录制、close 后发布 manifest；未读取 physics.json/report.json。候选仅对这一确切旧格式视频兼容，复用现有路径隔离、签名与 HTTP Range handler；未来视频要求完成/连续/哈希字段。**不是开门成功、不是 Isaac 结果，也未宣称已从正式网页播放。**

测试证据：

- 14 项 IKEA 隔离 fixture 测试通过：旧状态/心跳/重启、新 schema 及工程师实际格式、缺字段、终态分类、暂无录像、完成视频核验及撤销、非法路径/符号链接/错 hash/未封口视频拒绝。真实视频只做读取/ffprobe/hash，无录像修改。
- 第一轮基线 8 项旧页面 + 12 项 API/Range 回归通过。第二轮原页面测试出现 2 个失败：并发 owner 已获授权重开回答表单/提交，旧“无 form/不提交”断言失效。失败日志保留，未为了通过旧断言覆盖新版页面。后续应由该 owner 按新页面授权更新断言。
- 候选 JS 语法检查通过。**尚未完成候选合入后的真实 HTTP、10 秒播放保持和手机浏览器验收**；此项随统一合入与 UI 重启由唯一发布者完成。没有把 fixture 或候选核验写成生产上线验收。

实际交接：

- IKEA 工程师 `01a0a96b-06cc-7150-8c73-7b0897936b52`：第二账号 queue 一次字段合同请求成功，消息 `01a0a983-c286-7eb0-a307-3300f8a252fe`；不等其 ACK 才实现兼容。
- 唯一 UI owner `01a0a980-7943-7963-9f36-b9c43c90c2da`：由其 engineer.jsonl 的 thread.started 确认；候选与真实视频/字段证据 queue 成功，消息 `01a0a98d-083c-7c33-af8c-3691f8fff057`。请其自然边界合入、实际验收、只重启已确认 UI 并记录 ACK。

两项均为**已排队，未观察到本交接 ACK，未证实集成或上线**。没有中断/并发 resume 或为消费消息重发。不再为无变化状态轮询。源码前快照、并发 owner 改动快照、精确消息/回执 hash、公开投影及诊断录像证据均在本目录。

没有额外模型代理、付费 API、主账号调用、额度查询、凭据读取、环境安装，未修改机器人、预算或 skill。本有界辅助分支到候选交接为止；正式上线仍待唯一 UI owner。
