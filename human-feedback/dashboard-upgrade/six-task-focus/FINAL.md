已上线，ready=true。页面：http://127.0.0.1:8765/ 。最终部署时间：2026-09-16T12:54:28.829044+00:00；已核验网页 PID 1566910，原 tmux + tee 服务保持运行。

SIX-TASK-FOCUS-20260916 ACK（仅网页集成确认；不代表主管调度或skill加载ACK）。

IKEA与地面搬运显示“用户已暂停（已核验）”，依据固定 `pause-status.json` 中真实 actor/监督状态，不能仅凭PAUSE标记或零模型心跳生效。当前暂停与原EOF/HTTP429分开，原卡点可展开查看；原结果、影像、历史反馈均保留。暂停本身不创建人工求助题，不计成功或物理失败。

SIMPLE默认呈现原README对应六项精确入口选择。利用原受限campaign发现及同回合公共录制入口字段 `env_id`（投影为 `native_env_id`），与精确任务/审计回执一致后纳入；不读取或投影对象位姿等场景内容。XMovePick3保留H001-004人工辅助历史审计成功，XMoveBendPick保留实际回合证据。BendPickTeleop、BendPickSim、MobileCheezit、原十次木块和其他旧任务保留于历史/迁移区，不计MP、BetweenTables或当前新冻结测评。缺失精确入口记录时显示未知、未开始/待适配。

收尾发现主管新公开 `current_scope` 精确登记六项，已兼容并补验；页面区分“主管已登记范围”与“明确调度ACK/新回合和skill加载未上报”。没有把队列、管理状态或历史成功当加载/新测评。

验证证据：

- 先写7项失败复现（3断言失败、4缺字段错误），见 `tests-before.log`；最终8项定向测试全部通过，见 `tests-after.log`。
- 实际网页12项浏览器检查通过，包括精确入口、变体隔离、历史选择、XMovePick辅助分层、Range206、真实播放/跳转、刷新不重置播放位置、暂停历史和移动端。见 `qa-initial/browser-results.json`。主管新字段补验3项通过，见 `browser-final-results.json`，未重复未变化的媒体大套件。
- [六项目标截图](production-six-tasks.png)、[暂停与历史截图](production-paused-ikea.png)、[移动端截图](production-mobile.png)已逐张读取。
- `backup-manifest.json`、`changes.patch`、`preservation-after.json`记录备份、哈希和差异；反馈路由/存储、原媒体方法及播放器/表单提交函数未改，框架适配函数未改。两次重启均只针对身份已核验网页，首次证据在 `qa-initial/`，最终在 `restart-before.json`、`restart-after.json`、`final-health.json`。

本轮没有模型/API/物理请求、生产测试答案、对外队列消息，没有改actor、skill、预算、环境或原回执。只刷新公开状态并维护原页面。原任务负责人继续负责调度确认与新测评，网页任务到此完成。
