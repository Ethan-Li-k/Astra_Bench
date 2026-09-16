# 既有 R020 维护线程的有界继续工作

这是 SIMPLE 主控根据用户明确分工发来的交接；恢复同一个既有维护线程，不新建通用agent。保持第二账号run.sh、gpt-6-astra/xhigh、工作区沙箱/自动审批；无付费API、费用/额度查询、UI研究、新模型子线程、仿真或真机动作。读 AGENTS.md 与 ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md 到末尾，最新要求优先。每决策写三行，长任务tmux+tee，不截断完整推理。

具体任务：审查 artifacts/R019/coordination-request-door-frame-override.json，并在你独占的 tools/coordination 和 artifacts/R020 内最小维护现有 IKEA 门槛，使它能如实绑定正式推门使用的 asset003-exact-frame-four-boxes-v1。请不要因旧 original_physics=true 字面条件要求主控伪造物理未修改的声明。

证据已齐：
- artifacts/R019/door-frame-override-review.json 及其原始对照证据、rsi/simple_door_collision.py、tests/test_simple_door_collision.py（全部只读）。这是原始矩形门框凸包填洞的修复；只改固定门框碰撞表示，原资产文件、视觉/惯量、活动叶片/把手/铰链/接触参数和30度/1秒/站立/真实手接触准则保留。
- artifacts/R019/door-campaign/episode-0010/success_review.json、episode-0011/success_review.json，完整result/turn/skill/video/trace/scene/reset/hash证据。主控实际已审计2次独立成功；第0012轮还在执行，未计成功。
- 当前 tools/review_completed_door_episode.py 只复用你的 audit_trace 产生host审查，不另建gate、不登记IKEA。

要求：
1. 保留旧原始碰撞schema/证据，不把修复变体称为原样native CloseDoor benchmark。对修复版本限定override id、source mesh SHA、明确验证证据及必要字段；未知override、缺字段/哈希改变必须拒绝。
2. 复用当前audit与独立reset、完整turn/skill、唯一执行者、视频完整性检查；不放宽成功门槛。只有3次真正host审计成功后才能登记物理门槛通过。
3. 主控负责签发本线程所需的host enrollment/provenance receipt。请提供精确新版格式/命令与验证结果，不代主控伪签确认，不把上述2次写成3次，不启动IKEA。
4. 不修改 rsi/*、tools/learn_*、任何SIMPLE campaign原始证据、共享core、ground-to-table写域或现有接续器。不重复角色研究、不加新resume watcher。已有消息队列的同一请求视为同一任务，避免重复执行。
5. 完成后保存明确交付状态与文件路径（例如 artifacts/R020/frame-override-review-delivery.json），让主控消费。API/费用问题不在本有界任务内，不能调查或用其阻止物理版本schema工作。

本次只处理这一具体登记兼容性问题。完整等待本turn自然结束，记录真实限制和测试；无自动重试。
