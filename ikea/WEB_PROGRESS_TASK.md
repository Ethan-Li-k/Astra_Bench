# 给原UI辅助工程师：在现有网页接入IKEA进度

用户最新明确要求“继续推进，并且在网页端给出进度”。你上轮已完整完成API地面块进度区，本轮在同一辅助thread继续小范围修改现有站点 `human-feedback`。不要新站点、Canvas、框架或依赖。只用辅助账号run.sh gpt-6-astra/xhigh，不付费API、不主账号、不改机器人/预算/skill。不重新开发原Range/Host/Origin/白名单防护。每次决策三行；长任务tmux+tee。

本地主机在09:08UTC左右重启；旧进程全部消失，日志保留。父会话已于09:15恢复rsi-human-feedback-h001，原入口 http://127.0.0.1:8765/，不得把旧PID当现进程。其他分支状态也可能因重启过期，不能显示为已证实运行。只重启已确认的UI服务来加载本轮路由，不操作其他tmux进程。

写域：现有human-feedback/ui与tools所需少量文件，本轮证据 `ikea/web-progress-verification/`。先核实其他writer，snapshot与你上一轮发布版本有差异的文件；保留已有全部视频/反馈/API区。IKEA工程师正在同辅助thread 01a0a96b-06cc-7150-8c73-7b0897936b52恢复，不修改你的网页；你不改它的物理/状态代码。其state.json现为公开工程状态，heartbeat.json只证明心跳，不证明实际进展。

立即新增 #ikea-progress 区及 /api/ikea-progress 只读精选路由：
- 显示任务链卧室门→苹果→冰箱→放入，各项未有审计证据均“未验证”；当前物理后端/变体、工程阶段或推理/动作/系统中断状态、真实独立尝试数、审计成功数、动作数/模拟秒（没有就未知，不编0）、最后实际进展时间，与心跳/页面获取时间分开。
- 来源优先 `ikea/web-progress.json`（工程师将提供），兼容当前 `ikea/state.json`、heartbeat.json、`recovery-20260916/incident.json`与recovery-ack.json。仅精确白名单字段，禁止递归暴露路径/host真值/原始日志/认证。没有live证据的旧inference/continue不得表述成确定运行；显示最近已知状态及更新距今时间，不因慢推理超时/重试。
- 当前可显示MuJoCo FBX-derived no-latch v1、编译成功/物理校验中，0策略尝试/0审计成功，原USD关节仍未知；不要宣称完成了真实开门或Isaac结果。网页也明确此次主机重启，原API地面块旧状态只列最后已知进展，不能心跳替代进展。
- 每10秒刷新；仅任务阶段、真实终态或需人工介入变化时页内通知，不逐调用刷屏，不重建正在播放的video，不触发模型/机器人/重发请求。显示工程仍在等待的准确状态，非隐藏API机制长文。
- IKEA `video-manifest.json` 为将来已完成视频入口。只接受IKEA固定写域下稳定存在并完成标记/ffprobe可读的连续录像，核验元数据/hash/稳定签名并安全Range访问。类别区分诊断、学习、审计成功、人工辅助；未结束的视频不发布。没有IKEA视频时显示“首个连续视频尚未完成”，不能用SIMPLE视频冒充。保留现有视频。
- 页面提供清晰IKEA锚点链接，可在现有导航加入口；布局沿现有风格，手机宽度可读。不要将未验证物体坐标、源码或绝对私有路径放页面普通流程。

验证：复用上一轮针对性测试；加入无新schema/正常新schema/旧心跳与重启/未提供字段/终态分类/暂无录像/非法媒体路径拒绝/原视频Range未退步，浏览器核查10s自动刷新及现有视频不重置、IKEA清晰可见。纯fixture测试不得改生产状态或host证据。新视频若尚无真实输出仅测试fixture并如实报告，不谎称物理录像完成。

与IKEA工程师通过第二账号queue发一次字段合同请求，可读ikea/inbox.md，不等ACK而阻塞兼容state.json的上线。不要唤醒主账号桌面会话。变更完成后只重启已确认UI服务，验证真实HTTP及浏览器，输出本轮URL、测试/是否重启/真实状态、记录UI-RESULT.md及state.json后结束有界UI任务。父会话会打开页面，不要为无变化无限轮询。


## 新发现的页面并发所有者
紧急写域协调：父会话发现另一辅助工程师正在tmux rsi-dashboard-upgrade-0916执行human-feedback/dashboard-upgrade/run.sh。当前原网页服务已恢复PID59551。请立刻只读其TASK/日志取得thread并协商唯一页面写入者；在未确认前不要写共享server.py/index/app.js/style.css。你的IKEA适配可在ikea/web-progress-verification独立候选完成并交由该owner集成，避免重复总览或并行覆盖。读取本条也写ACK。不要中断任何在途模型/机器人。此消息也写入你的任务文件末尾。


## 页面单写者协调（父会话2026-09-16）
总览辅助thread01a0a980-7943-7963-9f36-b9c43c90c2da独占human-feedback/ui及tools发布。旧UI辅助thread01a0a961-11df-7a92-963d-4c9a1dcf2d94仅做IKEA状态的只读兼容审查/隔离候选，不写共享页面、不重启UI。队列消息已发送，尚未ACK。IKEA父会话已恢复网页PID59551，应以实时health核对。主机重启事件见ikea/recovery-20260916/incident.json。
