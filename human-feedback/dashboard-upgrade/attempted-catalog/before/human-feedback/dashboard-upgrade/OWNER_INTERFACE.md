# 四任务网页：执行者接口（仅 UI；2026-09-16）

地址：http://127.0.0.1:8765/ 。每5秒只读刷新，不启动模型/物理。
本次用户明确授权浏览器回答：仅新增 `/api/feedback`；旧 H001/F001 问卷继续关闭。

当前问题：管理状态、实际动作、录像封口时间不同步；人类回答必须可追踪。
总目标：让用户看懂四任务、看连续录像、按同信息证据给建议。
不可重犯的错误：不截断在途推理，不把排队当消费，不把预算/提前结束凑成三次物理失败。

## 公开状态与媒体

优先读取原路径：SIMPLE `codex-account-2/continuation/supervisor-state.json`、五个已知 `artifacts/R019/*-campaign`；ground 原 `auxiliary-progress.json` 与 `APIProgress`；IKEA `state.json`/`heartbeat.json`；framework 原 result、memory-priority result、no-truncation status/progress/result（较新公开结果优先）。
页面不读取 app_server/agent 日志或推理正文。审计文件仅提取计数、成功/终止分类、reset/控制版本字段；不进入反馈消息。
SIMPLE每个episode可选补 `public-progress.json`：`{"state":"inference_waiting"}` 或 `action_executing`。只在既有自然边界写；缺少标记显示未知，不能从心跳推断推理。
已知episode的 `rollout/episode/observations/NNNN/observation.json` + 原始 `head_stereo_left.png` / `head_cam.png` 自动显示；文件时间标为导出时间。公开 `execution_NNNN.json` 的文件时间表示最近动作证据。
`result.json` 在录像关闭后产生；`video/episode.mp4` 经 ffprobe 和文件签名核验才发布，默认显示每场景最新完整录像。正在写的录像不发布、不转码。原API进度/历史媒体URL保留。
IKEA未来连续物理episode可放 `ikea/campaign/episode-NNNN/`，采用相同public observation/result/video目录；如果实际管线不同，给UI工程师准确公开路径，不改运行中录制器。静态预览、工程诊断不能当策略尝试。

## 人类回答与确认

原话：`human-feedback/dashboard-upgrade/feedback/answers/FB-<uuid>.json`，只增不改，mode444、原子fsync。
提交包含任务、case或主动补充、source_version、原文/选项、用户时间、request_id、correction_of。同一request_id同内容只保存一次；更改内容拒绝。纠正新建记录并引用旧记录。
证据包：`feedback/packages/<source_version>.json` 是网页公开字段；不要回传隐藏审计。
通知仅经第二账号 `codex-account-2/run.sh queue -m gpt-6-astra -c model_provider="openai" -c model_reasoning_effort="xhigh" --thread <固定owner> --message <固定绑定消息>`，subprocess argv，绝无shell、resume或新model调用。消息给出回答和证据包路径及哈希，原文只从文件读。异常或不确定投递不自动重试；保存不丢失。

在自然边界消费后写新的不可变 `feedback/acks/FB-<uuid>-<unique>.json`：

```json
{"feedback_id":"FB-...","owner":"固定辅助thread ID","answer_sha256":"回答文件SHA256","stage":"owner_ack","at":"ISO8601","note":"已读；计划在下个自然边界验证"}
```

后来实际使用人工反馈，episode由owner标 `human_feedback_used=true`（不追溯改旧回合）。物理检验后另写：

```json
{"feedback_id":"FB-...","owner":"固定辅助thread ID","answer_sha256":"回答文件SHA256","stage":"physical_verified","human_feedback_used":true,"at":"ISO8601","evidence":"artifacts/任务/新回合/result.json","note":"实际检验结果与适用边界"}
```

网页独立显示保存、排队、owner ACK、owner报告物理验证；ACK不是成功。stage=physical_verified表示进行过实际验证，成功/失败在note中明确。
固定owner：SIMPLE `01a0a867-d7aa-71f2-8547-e264d6d09ede`；ground `01a0a982-cec5-71c0-b771-091c31df61f2`；IKEA `01a0a96b-06cc-7150-8c73-7b0897936b52`；framework `01a0a94d-6143-74c0-80cd-03d0b61acaf0`。

## 代表性失败题（没有符合条件的题就不问）

仅发布>=3不同reset、同机制/控制版本、真正终态物理失败、自主尝试且分析仍未解决的簇；回放、诊断、预算、提前结束不算。H001/F001已回答，不重复提出。主动补充不受门槛限制。
case schema见 `human-feedback/tools/feedback_board.py:validate_case`；工具 `create_help_case.py --input <候选JSON>` 做校验并不可变创建。候选含 `case_id=HC-*`、task_id、title、mechanism、control_version、question（一个有区分力的问题）、choices、facts、hypothesis、already_tried、unresolved=true、attempts。每attempt须引用公开adapter记录id/result_sha256/reset_id，continuous video URL、关键秒数、公开keyframe URL、change/outcome。
已有success_review/failure_review只投影独立reset标记与control_version/mechanism；未来owner须明确登记这些字段。网页校验实际result终态，不只相信case自报“三次”。不接受隐藏host数据字段。

## 工程交付 ACK

本说明是UI-only工程交接，不是人类答案。三位owner以及framework维护者在各自公开状态/回执写 `DASHBOARD-20260916 ACK`、状态/视频路径、是否可消费本目录回答、最近episode与自然边界。也可在本目录 `owner-acks/<task>.json` 写公开回执。不要因此中断推理、热改actor、并发resume或接管别人的源码。

## 2026-09-16 主控授权更新与短状态字段

ROOT_FINAL_REVIEW.md 明确授权将 ground 固定收件人更新为 `01a0a982-cec5-71c0-b771-091c31df61f2`，依据 auxiliary-progress.json、recovery-20260916/RECOVERY.md 和 owner-acks/ground.json；已覆盖最初旧白名单限制。旧 `01a0a948-10bb-7d03-8f1d-b1eeda7cb93c` 的队列/历史回执保留，不自动重投历史用户回答。其它负责人不变。工程交接 ACK 不追认为用户回答 ACK 或物理验证。

在既有公开状态中可选提供 `current_problem`（当前卡点/等待）和 `next_step`（下一步），短文本各最多展示600字，无须新平台。SIMPLE读最新回合 public-progress.json；ground读 auxiliary-progress.json；IKEA读 web-progress.json/actor-progress.json/state.json；framework读 no-truncation 的较新 progress/result/status。兼容已有 problem/blocker、next；ground兼容 recovery_note、IKEA兼容 engineering_state。缺少字段明确显示“尚未上报”。这些字段只说明执行者报告，不据此增加成功次数或触发动作。

SIMPLE旧门15的固定协调摘要只在同一未封口回合且无较新负责人状态时覆盖当前状态；有较新的公开状态则优先负责人。旧回合重启中断摘要保留为历史，标注“负责人报告”，不沿用到新的独立回合。读已知恢复回执只投影中断/预算类别，不公开宿主详情或隐藏审计正文。

## 2026-09-16 发布者来源同步

框架页以 `artifacts/R019/instruction-cap-integration/status.json` 的明确 applied / NT 部分采用回执判定 SIMPLE 部署；较旧审查候选未部署标记不会撤销发布事实。门16、水龙头8仅投影回合与独立审计是否通过，嵌套host_review/宿主细节不进入页面。共同变更的功能回归不作单因收益或泛化结论。`permission-contract-fix.json` 表示下一新reset权限边界；audit-compat的离线回执不代表发布或共享core晋升。

SIMPLE保留原五项顺序，只为明确许可的 `artifacts/R019/oven-campaign` / `simple/G1WholebodyOpenOvenTeleop-v0` 加一项烤箱；有真实动作回执或result动作数才出现，空目录/预检不算尝试。没有新增任意注册入口，也不展示91项未尝试库存。已存在campaign_audit只匹配这六个固定目录；不跟随其中video/result任意路径。最新回合的current_problem/next_step可由public-progress、campaign_audit同回合/任务字段补充；PROGRESS.md只解析固定任务/回合行的公开阶段和物理时间。封口结果优先于残留的活动状态，不从原生成功自动增加独立审计成绩。
