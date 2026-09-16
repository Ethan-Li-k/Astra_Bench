# 六项专页公开来源与计分边界

旧 URL http://127.0.0.1:8765/（含 #ikea）不变；新 URL http://127.0.0.1:8765/simple-six。
同一 Python 服务、同一 /api/dashboard 和 /api/feedback，无额外服务或外发渠道。唯一 UI 发布者集成；不改 actor。

只从现有受限 campaign_audit 清单和 Dashboard 验证过的精确原生入口读取回合；结果、success_review/failure_review、scene_setup 的入口/初始化/控制/reset/反馈标记、policy_instruction_budget 的 hash 只投影必要字段。scene 对象真值、host 审计内容不输出，不跟随来源字符串中的路径。

成功率按当前范围 / 历史、人工辅助 / 自主 / 未知、声明的初始化变体 / 控制 / 完成合同分组。学习内 skill 可以变化，显示版本数；该累计描述不是固定策略可靠性。每个率展示成功数 / 完整封口且独立审计的有效尝试。原生结果与完整任务审计分别读取；实际 episode_step_budget + budget_truncation 且完整审计计有效未成功，安全停止同理。未封口、缺身份/审计、系统中断、暂停、重放、重复 reset 分别列出，不静默缩去未判定记录。当前范围边界来自六项 owner ACK 的 effective_utc；旧在途保留历史层。

当前没有实际登记的固定候选 / 冻结批次，连续数为 null，冻结分母为 0，页面显示未登记 / 未测评，默认计划 10 不计作已执行。不会从旧成功或排队回执回填 5 次稳定性。

可选兼容字段仅供原 owner 的公开回执投影，不由 UI 创建登记：已验证 campaign/progress.json 的 candidate_manifest 内含 protocol=SIX-TASK-FIVE-STABLE-V1、精确 native_env_id、locked=true、registered_at、human_feedback_used、candidate_sha256 与 config_sha256。config_sha256 为 skill/entry/runtime/memory/retrieval/feedback/task_asset/control/camera/model 的完整 64 位 hash；candidate_sha256 为该映射排序、紧凑 JSON 的 SHA256。预登记 stability_reset_ids 5 个、frozen_reset_ids 10 个且不重复不交叉。固定回合 evaluation-manifest.json 需同 config/hash、loaded=true、config_unchanged=true，匹配真实结果 starting_skill_sha256/runtime_sha256、reset 时间与反馈层。缺失或冲突保持未知。此为只读兼容，未声称与 owner 新字段已经协商或上线；未来不同格式需先核对真实合同，不能把任意 ready/成功状态视为完整配置冻结。

新页主动反馈复用原 append-only 提交，仅可增加 context={subtask_id,native_env_id}，服务器验证其匹配已固定 source_version 的六项记录；原话不加前后缀，原 payload 继续兼容，原 owner allowlist/queue/ACK/物理验证语义不变。案例回答保留原同回合证据绑定，不附加主动反馈上下文。测试只使用隔离 fixture；未产生生产答案或队列消息。

启动：在 RSI 执行 bash human-feedback/tools/run_server.sh，原 tmux rsi-human-feedback-h001，沿用 tee。重启前必须核验 server-status.json、/api/health、进程 cmdline/cwd 与 tmux 身份；不能操作用户浏览器或机器人。
