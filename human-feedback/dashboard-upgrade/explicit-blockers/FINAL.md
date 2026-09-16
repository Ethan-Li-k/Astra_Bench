已上线，ready=true。页面：http://127.0.0.1:8765/ 。部署时间：2026-09-16T11:43:29.723599+00:00；最终身份核验网页 PID 1069908，原 tmux + tee 服务持续运行。

仅修改 `human-feedback/tools/dashboard.py`。搬运优先展示同回合的 HTTP 429 具体回执，通用监督状态降为补充；保留远端请求结果/费用未知、未知请求不重发，以及抓取/搬运/放置尚未验证。旧回合、不同 run、较旧的同回合卡点不能覆盖新执行状态，回合和请求次数直接来自公开源。

框架仅接入固定 `robot-stability-observation/manager-status.json`、`progress.json`、`result.json` 的短状态字段。当前显示本体高度/倾角与安全停止判据的离线候选审查；未部署、物理收益未验证。以后 ready + candidate-only 只显示候选已交付、待发布者。NT 已发布、门19已加载、真实断线恢复未验证及其他已发布里程碑均保留。候选来源时间取实际文件时间，单独标注管理状态非物理动作。

验证结果：

- 修复前先运行12项定向测试，6项未通过（3项断言失败、3项缺字段错误），完整保留于 `tests-before.log`；修复后12项全部通过，见 `tests-after.log`。
- 实际8765页面14项浏览器检查通过，见 `browser-results.json`；[搬运截图](production-ground.png)和[框架截图](production-framework.png)已逐张读取确认。表单可用，本轮未填入或提交任何假答案。
- `preservation-before.json` / `preservation-after.json` 核对 UI、服务端、反馈存储/路由、API/媒体适配源文件及其他任务/媒体方法均未变。未重跑无关全套测试；沿用原46项、19项和后续专项媒体/反馈验收证据。
- 备份与哈希见 `backup-manifest.json`，改动见 `changes.patch`，最终源码哈希见 `source-manifest.json`，身份核验见 `restart-before.json` / `restart-after.json` / `final-health.json`。

首次浏览器QA因调试端口未建立提前退出；缩短本任务目录内临时socket路径后成功，初次日志仍保留。本轮未发送工程广播、未改反馈收件人、未部署候选、未调用模型/API或操作机器人及在途任务。HTTP429后续处理与候选发布仍由各自负责人处理；页面只投影已有公开证据。
