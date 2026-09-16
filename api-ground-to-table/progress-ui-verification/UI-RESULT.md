# 只读 API 进度区与三方交接完成

入口：http://127.0.0.1:8765/#api-ground-progress 。首批完整录像：http://127.0.0.1:8765/#api-ground-episode-0001 。公开数据：http://127.0.0.1:8765/api/ground-progress 。仍为既有页面、既有服务，没有新框架/依赖/站点/Canvas，标注保持关闭，原内容与反馈保留。

新增区每 10 秒刷新 run/episode、推理或执行状态、API 完成数、真实动作、物理秒、更新时间、物理暂停与终态分类。没有显式公开任务子阶段时显示未提供；抓取、持物搬运与放置均标未验证。页内阶段/回合终态通知不按调用数弹窗；未更新只显示时长，不做推理超时或重发，不声称后台聊天通知。更新 DOM 不重建 player，不修改其 src 或播放进度。

只读精选 auxiliary-progress.json、对应 result.json 与已存在的 public_history_index.json；实际后端从当前 provenance 的 backend 标量读取。没有读取 host_audit 或凭据。首批 episode-0001 为 6 API / 3动作、预算截断未完成；已通过 ffprobe、读取前后签名及 SHA256 核验并可 Range 播放。验收快照中第二批为 MuJoCo、38 API / 16动作 / 76.68物理秒、推理中物理暂停，尚无 result，不发布其在写录像；后续随原 owner 写出 result 且固定录像核验通过动态加入白名单。快照不是后续实时进度承诺。

安全与保全：原三视频白名单/Range、loopback 绑定、精确 Host/Origin 校验、关闭的提交接口均保留；新媒体只允许固定 episode 路径且拒绝符号链接，源变更撤销已核验资源。来源只提供路径标识和哈希，不开放目录/任意文件。35 个原案例、反馈和视频索引文件哈希不变。旧源码存 before/，增量见 ui.patch，来源与服务证据均在本目录。

验证通过：8 项原视频回归 + 12 项新增针对性后端/HTTP 测试；10 项真实 Chrome 检查覆盖 10 秒刷新时视频持续播放、终态变化通知、调用数变化不通知、陈旧推理不标失败、后台读取错误保留上次状态、移动端布局及无运行异常。正常推理、无 result、预算截断非失败、后台终态错误、未封口视频、源篡改撤销、旧/新视频 Range、任意路径与 Host/Origin 拒绝均有覆盖。首次浏览器测试因测试脚本 CDP 顶层 await 语法问题中止，修正为 async IIFE 后通过，首次失败日志保留于 browser-check.log。

服务仅重启 **rsi-human-feedback-h001:0.0 一次**：旧 PID 2715603，新 PID 3676564；重启前核验 health、pane 与祖先链，旧日志副本保留且原 server.log 前缀未被截断。未启动、停止、重启或控制任何机器人/actor/模型任务，未改 actor、budget、skill。前后只读快照中 7 个相关 pane PID 一致；simple-faucet-07-0916 在后快照不再出现，本 UI 任务没有对它发出任何控制操作，未调查或推断退出原因。测试 Chrome 自然关闭，UI 保持运行。

三方交接实际状态：

- API 工程师 `01a0a948-10bb-7d03-8f1d-b1eeda7cb93c`：第二账号 queue 成功，消息 `01a0a96b-b335-7111-b5ee-3f9b7a7a6252`；包含 CONTINUATION、ARCH-REVIEW-20260916-V1-API、memory-priority 候选与 UI 入口，要求自然边界 ACK/分享经验/在原批准边界继续有区分力尝试。
- 辅助审查 `01a0a94d-6143-74c0-80cd-03d0b61acaf0`：在工程师入队确认后顺序 queue 成功，消息 `01a0a96b-b452-7353-844f-7cb8f90ea899`；转达最新方向和公开 API 证据索引，明确未 ACK 不称集成。
- SIMPLE owner：用 apply_patch 只追加已证实消费的 artifacts/R020/supervisor-inbox.md，请求经审查的控制/locomotion/站位/持物移动候选及 task/controller/contract hash、证据、前提与不适用项；未要求暂停或改变任务/预算。原内容保留，精确字节段和哈希见 inbox-delivery.json。

上述均只算 **已排队**；一次有界公开日志尾部检查未观察到本次交接标记或 ACK，不能证明活跃长 turn 会即时消费。未终止/并发 resume、未重发、未启动接续器。收件人可在自然边界处理；读取 ACK、集成和真实物理验证仍分别待 owner 记录。实际 queue 回执、消息全文字节哈希、来源文件段哈希见 queue-status.json、queue-*-receipt.txt、handoff-source-hashes.json。

本 UI 有界任务至此完成；不继续轮询机器人或等待 ACK。没有额外模型代理、付费 API、配额查询、凭据读取或环境安装。
