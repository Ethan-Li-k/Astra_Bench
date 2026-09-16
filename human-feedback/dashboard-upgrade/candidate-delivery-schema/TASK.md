当前问题：你的explicit-blockers工程turn已完整完成；root在该回合排队的真实schema反馈尚未消费，实际页面仍错把已交付候选显示为offline-review。总目标：只修这一个已复现的真实源格式兼容；不可重犯：不修改原候选回执、不重跑不受影响大套件、不扩范围、不改变NT发布/物理验证状态。

直接读取human-feedback/dashboard-upgrade/explicit-blockers/actual-candidate-schema-delivery.json里的root说明及artifacts/architecture-review-20260916/robot-stability-observation/{result,progress,manager-status}.json。真实result无ready，使用status=candidate_only且delivery.queued=true/acknowledged=false/integrated=false；progress stage=bounded_delivery_complete。原detected=result.ready && candidate(state)不匹配，已确认缺陷。只改dashboard.py的stability_observation函数，用匹配candidate_id和明确完成阶段/交接组合识别“候选已交付；待发布者审查集成”，未知组合不假定完成。不要依赖root-review或engineer日志作为公共数据。当前problem/next也不能继续采用较旧manager“正在核对”；交付后应简洁中文说明观测候选完成、等待唯一发布者自然边界检查与集成、未部署/物理收益未验证。不能把queued当ACK。

复用既有原12项fixture和网页服务重启/浏览器脚本；增加覆盖真实result/progress组合的一项回归，先记录旧版本错误、再通过。只做与新格式和NT状态保持有关的浏览器验证2-3项，不再泛测HTTP429/媒体/反馈，也不新搭浏览器诊断平台。检查实际8765框架确实显示候选已交付且未部署，保存1张截图并读图，核验UI进程身份后重启，保留网页运行。root已确认候选20离线测试、唯一publisher队列和完整turn，不再研究候选实现/机器人。

始终当前第二账号openai/Astra/xhigh；只改本地UI与本目录，不碰actor/skill/候选/阈值/预算/环境，不发模型/API/物理请求、不新建子代理或桌面任务。无需对外queue。本目录result/FINAL写ready并完整结束有限turn。
