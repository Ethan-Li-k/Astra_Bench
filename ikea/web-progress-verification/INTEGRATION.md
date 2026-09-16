# IKEA 增量候选：等待唯一 UI 发布者合入

检测到 `rsi-dashboard-upgrade-0916` 正在修改相同 tools/ui；为避免争写，目前仅写本目录，未改在线源码/重启服务。用户已收到发布归属问题。IKEA 工程师字段合同请求已通过辅助账号 queue 一次送达（仅排队），不等待其 ACK 阻塞兼容实现。

候选 `candidate/ikea_progress.py` 依赖现有 `api_progress.APIProgress` 的安全读取/路径约束/锁及签名工具；不导入机器人代码。兼容 `schema_version:1` 与工程师实际 `schema:1`、旧 state、heartbeat、重启 incident 与 recovery ACK。固定字段投影，原始文本/日志/host 真值不出浏览器。心跳与进展/获取时间分开，旧 continue/inference 不表述成确定运行。

合入当前 server 的最小改动：

1. 将 `ikea_progress.py` 放 tools，`from ikea_progress import IKEAProgress, last_known_runtime`；`make_server` 构造 `ikea=IKEAProgress()`。
2. `/api/ikea-progress` 调用 `ikea.snapshot()`；`/api/ground-progress` 原 payload 经 `last_known_runtime(api.snapshot(), ikea.boot_started_at)` 标记旧进程状态，保留原 terminal_kind/result 和媒体。
3. `/videos/ikea-...` 只调用 `dynamic=ikea.video(path)`。有精确白名单元组就复用原 `self.video(path,dynamic)`，否则404。不改 Range、Host、Origin、loopback 或旧路由。
4. 将 section snippet 融入原页面，加清晰 `href="#ikea-progress"` 入口；将 `ikea-ui.js` 放 ui 并添加精确静态路由/脚本。其定时读取只更新文本/候选视频列表，不替换正在播放的 video。若 dashboard 已有统一 renderer，可直接按同字段渲染，避免重复轮询。
5. API 区加 `runtime_notice` 及“最近记录”的暂停状态标注，明确本次主机重启。页内通知只依赖 IKEA phase / terminal_kind / needs_human。工程诊断计数与策略尝试分列。

未来 manifest 采用字段请求中 completed/continuous/sha256 形式。已真实出现的 `diagnostics/door-v1-001/video/episode.mp4` 有单独兼容路径：已只读检查 validate_door.py 在每个真实 tick 调用 EpisodeVideo.record_tick、finally close 后才发布该精确 manifest row；其 schema1/complete/kind 格式可通过 ffprobe、读取前后签名和计算 SHA256 发布为**诊断**。不读取其 physics.json/report.json，不计策略成功；未知旧格式视频默认不发布。manifest 中绝对路径仅在内部核对位于固定 IKEA 写域后转为相对来源，普通 UI 不显示私有绝对路径。

`test_ikea_progress.py` 的 fixture 位于本目录；旧 API 回归通过导入后覆盖测试的 EVIDENCE 目录重用。正式发布前还须对合入版做实际 HTTP/Chrome 检查；未部署不写 ready。只允许由确认后的唯一 owner 重启现 UI 一次并保留旧日志。
