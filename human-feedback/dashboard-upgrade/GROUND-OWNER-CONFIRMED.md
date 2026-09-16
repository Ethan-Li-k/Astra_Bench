# 根协调确认：搬运反馈映射接续

当前问题：四任务网页已交付且根已实际浏览验证；ground目前仍通知主机重启前的旧owner，新映射等待根协调确认。
总目标：用户“继续推进，并且在网页端给出进度”，让网页中的地面物块搬运建议到达当前唯一辅助执行者；不改变其他任务。
不可重犯的错误：不唤醒主账号，不重发不确定的旧消息，不把工程ACK或入队当人工回答已消费，不停止机器人进程。

这是根协调者确认，不冒称新的用户逐字指令：当前ground唯一执行owner为辅助thread `01a0a982-cec5-71c0-b771-091c31df61f2`；旧 `01a0a948-10bb-7d03-8f1d-b1eeda7cb93c` 随本机重启消失且不再使用。现owner在 `rsi-ground-followup-0916` 通过第二账号run.sh resume，thread.started和公开ACK已核对，任务是复盘003、继续新尝试并补齐持续监督。你本人上轮turn.completed已确认，故本次仅resume原UI辅助thread，不新建并发owner。

请在原UI写域做最小修正：更新ground固定路由与可见说明/OWNER_INTERFACE，保留变更时间和证据；未知/旧收件人的已保存回答及排队回执原样保留，不能重写为已投给新owner、也不自动重发。新增回答走新owner，仍只queue不resume。其余SIMPLE/IKEA/framework映射不变。用隔离fixture断言新路由、旧记录不变、无生产假答案；记录测试与当前服务版本。确需重启只重启你拥有的网页服务，不动任何仿真或推理。浏览器验证ground页仍可播放episode-0003，刷新不重置视频，反馈表单可见且不再提示新owner待确认。

根已核验003：result为safety_stop/diagnostic_stability_stop、10API/5动作/18物理秒、无抓取/携带/放置成功；h2641280×544、18.04秒完整视频，页面已有该视频。旧002重启中断须继续单列、不计物理失败。搬运监督当前复盘，新动作没发生前不更新最后动作时间。你不要替owner写复盘、修改actor或shared skill，也不扩建网站/新增架构。若当前投影暂只显示003终态，保持真实，不伪造新回合运行。

固定辅助账号gpt-6-astra/xhigh，不查费用/额度、不API请求、不内建subagent。沿用原TASK及验证约束。完成后保存OWNER-MAPPING-RESULT.md，向新ground owner发一次有明确工程标记的queue交接；实际人类答案确认与验证仍由owner另记。只完成这一有界映射修正。
