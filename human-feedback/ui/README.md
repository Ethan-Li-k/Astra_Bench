# RSI 视频与进展（只读）

本机打开 http://127.0.0.1:8765/ 。页面服务器继续使用 `rsi-human-feedback-h001` tmux与8765端口；没有新仿真、模型调用或账本写入。

首页现在只有真实视频、简短来源/时序/视角说明和已收到的反馈。H001三条原话已导入并可通过annotation ID核验；F001反馈保留在协作分支原文件，页面只读呈现。没有表单、待答字段或催答。旧 `/api/case` 与浏览器提交入口返回410，防止已打开的旧表单继续提交。原不可变标注及冻结case均保留；旧UI/交付在 `reviews/history/pre-video-home/` 标为历史。

人工求助关闭：至少3次可比、真实、独立探索仍未解决并完成自诊断后，才审核代表性失败。固定旧动作基线、回放、接口错误、多个视频或文件不计作3次。尚无本页可用的已审核失败簇，计数为未知而非伪报0；界面不会自动放行。

视频索引：`video-index.json`（也可 GET `/video-index.json`）。只提供三个精确路径：

- `/videos/simple-door-0008.mp4`：66.12秒、1280×424，完整物理录像，可能包含外部诊断视角，不据此声明推门成功。
- `/videos/h001-closure-lift.mp4`：13.84秒、640×360，新动力学基线的头部左目连续片段，模拟205.925–219.765秒。失败已复现；不是修正成功。
- `/videos/f001-baseline.mp4`：7.48秒、1280×544，连续旧动作物理基线；左为外部track诊断视角，右为head_cam。协作分支录像实现及公开说明已核对。

`actor-observations.mp4`是精选RGB静止帧序列，本页未用其代替连续录像。H001实际状态每次GET `/api/progress`从复现分支状态读取，服务仅返回公开筛选字段，不返回host路径或审计内容。视频Range/HEAD支持拖动；启动时核对SHA256，文件变更拒绝继续提供旧绑定。仅监听127.0.0.1，Host/Origin校验、精确白名单、无CORS、无出网客户端。当前是可信本机用户界面，不提供远程身份认证。

启动方式保持不变，勿重复启动已存在session或占用端口：

```sh
cd /home/galbot/lizekai/RSI
tmux has-session -t rsi-human-feedback-h001
# 仅在不存在且8765未占用时：
tmux new-session -d -s rsi-human-feedback-h001 'bash /home/galbot/lizekai/RSI/human-feedback/tools/run_server.sh'
```

`H001-feedback.canvas.tsx`同步改为只读进展入口，数据内联、只import cursor/canvas、无fetch，无第二份标注存储。当前无canvas渲染宿主，工作界面以真实Chrome验证的网页为准。未来求助审核按 `reviews/review-protocol.md`；本任务不改skill或启动复现。
