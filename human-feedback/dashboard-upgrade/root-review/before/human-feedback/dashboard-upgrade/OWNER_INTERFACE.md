# 四任务网页：执行者接口（仅 UI；2026-09-16）

地址：http://127.0.0.1:8765/ 。每5秒只读刷新，不启动模型/物理。
本次用户明确授权浏览器回答：仅新增 `/api/feedback`；旧 H001/F001 问卷继续关闭。

当前问题：管理状态、实际动作、录像封口时间不同步；人类回答必须可追踪。
总目标：让用户看懂四任务、看连续录像、按同信息证据给建议。
不可重犯的错误：不截断在途推理，不把排队当消费，不把预算/提前结束凑成三次物理失败。

## 公开状态与媒体

优先读取原路径：SIMPLE `codex-account-2/continuation/supervisor-state.json`、五个已知 `artifacts/R019/*-campaign`；ground 原 `auxiliary-progress.json` 与 `APIProgress`；IKEA `state.json`/`heartbeat.json`；framework 原 result、memory-priority result、no-truncation status。
页面不读取 app_server/agent 日志或推理正文。审计文件仅提取计数、成功/终止分类、reset/控制版本字段；不进入反馈消息。
SIMPLE每个episode可选补 `public-progress.json`：`{"state":"inference_waiting"}` 或 `action_executing`。只在既有自然边界写；缺少标记显示未知，不能从心跳推断推理。
已知episode的 `rollout/episode/observations/NNNN/observation.json` + 原始 `head_stereo_left.png` / `head_cam.png` 自动显示；文件时间标为导出时间。公开 `execution_NNNN.json` 的文件时间表示最近动作证据。
`result.json` 在录像关闭后产生；`video/episode.mp4` 经 ffprobe 和文件签名核验才发布，默认显示每场景最新完整录像。正在写的录像不发布、不转码。原API进度/历史媒体URL保留。
IKEA未来连续物理episode可放 `ikea/campaign/episode-NNNN/`，采用相同public observation/result/video目录；如果实际管线不同，给UI工程师准确公开路径，不改运行中录制器。静态预览、工程诊断不能当策略尝试。

## 人类回答与确认

原话：`human-feedback/dashboard-upgrade/feedback/answers/FB-<uuid>.json`，只增不改，mode444、原子fsync。
提交包含任务、case或主动补充、source_version、原文/选项、用户时间、request_id、correction_of。同一request_id同内容只保存一次；更改内容拒绝。纠正新建记录并引用旧记录。
证据包：`feedback/packages/<source_version>.json` 是网页公开字段；不要回传隐藏审计。
通知仅经第二账号 `codex-account-2/run.sh queue -m gpt-6-astra -c model_reasoning_effort="xhigh" --thread <固定owner> --message <固定绑定消息>`，subprocess argv，绝无shell、resume或新model调用。消息给出回答和证据包路径及哈希，原文只从文件读。异常或不确定投递不自动重试；保存不丢失。

在自然边界消费后写新的不可变 `feedback/acks/FB-<uuid>-<unique>.json`：

```json
{"feedback_id":"FB-...","owner":"固定辅助thread ID","answer_sha256":"回答文件SHA256","stage":"owner_ack","at":"ISO8601","note":"已读；计划在下个自然边界验证"}
```

后来实际使用人工反馈，episode由owner标 `human_feedback_used=true`（不追溯改旧回合）。物理检验后另写：

```json
{"feedback_id":"FB-...","owner":"固定辅助thread ID","answer_sha256":"回答文件SHA256","stage":"physical_verified","human_feedback_used":true,"at":"ISO8601","evidence":"artifacts/任务/新回合/result.json","note":"实际检验结果与适用边界"}
```

网页独立显示保存、排队、owner ACK、owner报告物理验证；ACK不是成功。stage=physical_verified表示进行过实际验证，成功/失败在note中明确。
固定owner：SIMPLE `01a0a867-d7aa-71f2-8547-e264d6d09ede`；ground `01a0a948-10bb-7d03-8f1d-b1eeda7cb93c`；IKEA `01a0a96b-06cc-7150-8c73-7b0897936b52`；framework `01a0a94d-6143-74c0-80cd-03d0b61acaf0`。

## 代表性失败题（没有符合条件的题就不问）

仅发布>=3不同reset、同机制/控制版本、真正终态物理失败、自主尝试且分析仍未解决的簇；回放、诊断、预算、提前结束不算。H001/F001已回答，不重复提出。主动补充不受门槛限制。
case schema见 `human-feedback/tools/feedback_board.py:validate_case`；工具 `create_help_case.py --input <候选JSON>` 做校验并不可变创建。候选含 `case_id=HC-*`、task_id、title、mechanism、control_version、question（一个有区分力的问题）、choices、facts、hypothesis、already_tried、unresolved=true、attempts。每attempt须引用公开adapter记录id/result_sha256/reset_id，continuous video URL、关键秒数、公开keyframe URL、change/outcome。
已有success_review/failure_review只投影独立reset标记与control_version/mechanism；未来owner须明确登记这些字段。网页校验实际result终态，不只相信case自报“三次”。不接受隐藏host数据字段。

## 工程交付 ACK

本说明是UI-only工程交接，不是人类答案。三位owner以及framework维护者在各自公开状态/回执写 `DASHBOARD-20260916 ACK`、状态/视频路径、是否可消费本目录回答、最近episode与自然边界。也可在本目录 `owner-acks/<task>.json` 写公开回执。不要因此中断推理、热改actor、并发resume或接管别人的源码。

## 2026-09-16 最终收件人核对

已收到 `owner-acks/ground.json` 的恢复负责人声明（新thread `01a0a982-cec5-71c0-b771-091c31df61f2`，可读取回答）。用户明确固定白名单仍是原ground thread，故未自动改投新thread；页面显示这一映射待主控确认。此文件只是工程交接ACK，不是任一真实用户回答的owner_ack，不追认物理验证。旧episode0002重启中断与损坏录像记录继续展示，不随新回合切换丢失。
