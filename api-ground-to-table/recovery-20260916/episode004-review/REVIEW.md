当前问题：004已因API流无终态事件停止；43不是完成调用，只有42个完整回执；后半段脚步停滞。
总目标：原桌位地面红块走近、站稳抓持、携物移动、桌面释放退手保持。
不可重犯的错误：不重发004未知43/002未知55，不将网络中断当物理失败，不将19动作当多个独立失败。

004有独立reset与完整83.08秒录像，实际后端MuJoCo。原result为infrastructure_error、native in_progress，未触发安全或物理预算停止。最后完整动作e4_019_roll_assisted_right_arc已执行，ACK timed_out、reference_finished=true；这是动作到位超时，不是模型推理超时。其后第42次模型结果完成，第43次API流自然结束却没有Responses终态事件，异常为Missing terminal response。socket timeout为None，未设置推理截止时间、未重试。旧传输没有保存事件类型统计，因此不能追溯判断是服务端、代理还是网络丢失，也不能确认远端推理已结束。

原sim已随actor退出关闭，没有完整sim/controller/在内存中的Responses history checkpoint；不能无缝恢复本回合。原43预留1217分保持，completion文件的内容是unknown_no_retry，文件名不构成已完成证据。API账本与004原文件哈希见host-integrity.json及original-episode-manifest.json；独立host诊断不进入policy。

公开物理复盘：低小弧线动作1没有脚步抬升。动作2/3/4分别产生左/右/左踝约118/101/131毫米推进、39/44/42毫米峰值上升；足部偏航从约-2/+1度累积至-22/+13度。后15动作改变腕部姿态、偏航、方向、时序或支撑roll，但未形成另一次脚位改变。整个回合公开骨盆倾角峰值低于14.4度，说明低倾角并非可继续步行的充分条件。手回撤确实到位，却没有恢复脚移动；近桌面手部干涉仅为视觉假设，不能断言接触或控制器故障。

下一候选005将在明确新批次授权及正常执行审批后独立reset，检验早期可见抬脚阶段保持/纠正方向，是否减轻足部相向偏航及后续停步。具体目标仍由直接API policy从新观测选定；若方向约束阻止清脚，或方向保持后仍停步，即反驳该候选。此为原控制合同空手候选，不能晋升为已掌握步态、携物移动或SIMPLE/IKEA成功经验。F001人类规划反馈分层保留；本次无新人工回答、无求助失败计数。

视频位于 `/videos/api-ground-episode-0004.mp4`；它包含外部诊断视角，不能当policy视野。公开经验只来自保存的原始头/腕相机、命名机器人状态、目标及ACK，关键原图副本在keyframes，统计和引用在review.json。

后续传输诊断遵循 [OpenAI streaming事件文档](https://developers.openai.com/api/docs/guides/streaming-responses)：终态事件与delta/流结束分开判断。新增诊断只记录白名单事件计数、HTTP状态、字节数及终态标志，不保存正文/私有推理，不设置deadline或重试；这不宣称修复了004尚不明确的远端故障。
