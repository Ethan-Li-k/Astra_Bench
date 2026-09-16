# 已尝试任务清单与 NT 发布维护交付

ready=true；http://127.0.0.1:8765/ 持续运行。部署时间 2026-09-16T11:10:16.241166+00:00；最终身份核验 2026-09-16T11:12:37.541349+00:00；UI PID 839565。

本次仅改 `human-feedback/tools/dashboard.py` 和 `OWNER_INTERFACE.md`。原六项ID、顺序、统计含义和媒体链接保留；UI布局、server路由、负责人映射、原回答/媒体、actor与技能未改。仅身份核实后重启网页，仍由原唯一发布者串行维护。

## 已交付

- 从既有campaign_audit自动发现实际尝试任务。只接受规范R019直接子目录、严格campaign basename和源声明的SIMPLE注册名；拒绝dotdot、外部、非规范、软链接、task不一致和ID冲突。清单physical_attempt/action声明还须有同回合正动作result或具物理时长的公开execution命令回执；预检、空reset和仅计数不显示为实际任务。
- 现有垃圾桶、椅子、XMoveBendPick已接入；随后源中新增的任务也在正常轮询中加入。浏览器截图时新增项为：simple/G1WholebodyBendPickSimToRealTeleop-v0、办公椅、垃圾桶、移动拾箱 XMoveBendPick、simple/G1WholebodyXMovePickTeleop-v0。不为未知名字编造中文语义，原样显示注册名；未知计数/目标保持未知。
- 动态目录映射同时用于任务行、预览/封口录像及case_media。原三次独立失败和同回合媒体绑定门槛保留，动态任务不只是展示卡片。
- 框架显示“续接审计已发布；门19已加载；真实断线恢复尚未验证”。NT-AUDIT publisher回执与三个after文件哈希确认发布；门19合同/network_continuation预留和指纹确认加载；physical_network_recovery_verified单独读取，不从成功、动作或视频推断。
- 63项发布者离线测试与真实网络恢复验证分开；权限状态现按正式物理动作公开路由回执显示。共同变更不作单因归因或泛化；不热改在途，共享core未晋升。

## 验证和证据

12项定向fixture通过：三个新任务、未来注册名、未尝试排除、非法/外部/非规范/软链接路径、task/ID边界、未知计数、封口优先残留等待、动态求助冷启动三回合、不同回合媒体拒绝、NT新旧来源优先级、发布/加载/真实恢复独立、权限动作与公开字段投影。首次测试发现连字符注册名被过严排除，已修复并保留初始日志。原未变化11/19/46项证据沿用，无全量重跑。

实际8765浏览器14项通过：四lane和原六项顺序、新任务选择、NT/权限文字及来源、垃圾桶公开原图和连续录像、Range响应、播放/拖动、5秒轮询保持播放位置、移动端宽度、反馈表单保留、无浏览器异常。无生产测试答案；合成求助只在隔离fixture。截图已实际查看。

[测试日志](tests.log) · [浏览器回执](browser-results.json) · [公开API快照](production-public.json) · [框架截图](production-framework.png) · [垃圾桶录像截图](production-trashcan.png) · [XMoveBendPick截图](production-xmovebendpick.png) · [移动端](production-mobile.png)。

[备份与哈希](backup-manifest.json) · [变更](changes.patch) · [保护文件校验](preservation-after.json)。11份保护文件/历史回执哈希不变；无actor/技能、机器人或推理变更，无模型/API实验、新环境或子代理。

## 工程交接

一次工程交接于2026-09-16T11:11:55.281708+00:00经第二账号run.sh queue确认排队，原SIMPLE owner `01a0a867-d7aa-71f2-8547-e264d6d09ede` 不变，显式openai/Astra/xhigh；不是人类回答。排队不计ACK、反馈消费或物理验证，旧回答/交接不重发。见 [队列回执](simple-handoff-receipt.json)。

后续实际任务按同一受限清单/动作证据自动刷新，真实断线恢复仍待明确回执。本次维护完成并结束，不等待其它机器人目标。机器回执：[result.json](result.json)。
