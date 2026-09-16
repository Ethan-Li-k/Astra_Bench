"""Publish a current, dated human status from state.json; archive every prior text."""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    state = json.loads((ROOT / 'state.json').read_text())
    old = ROOT / 'STATUS.md'
    archive = ROOT / 'status-history'
    archive.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    previous = archive / f'STATUS-{stamp}.md'
    if old.exists():
        with previous.open('x') as stream:
            stream.write(old.read_text())
    now = state['updated_at']
    body = f'''# IKEA 当前执行状态

状态时间：{now}。这是当前摘要；旧初始状态与逐次记录完整保存在 [status-history](status-history/)。

当前问题：{state['current_problem']}

总目标：棕色卧室门 → 桌面苹果 → 开冰箱 → 苹果放入冰箱组合。完整任务链尚未完成。

不可重犯：不重复启动/重发在途请求，不截断模型推理，不热改在途actor，不泄露host真值，不把派生物理称为原样USD或Isaac，不绕共享预算。

当前阶段：{state['phase']}；工程状态：{state['state']}。

模型：{state['model']} / {state['reasoning_effort']}。实际后端：{state['backend']}。

当前回合：{state.get('episode', '未开始')}，本回合动作 {state.get('actions', 0)}，本回合模拟 {state.get('sim_s', 0):.2f} 秒。全分支真实执行尝试 {state.get('physical_attempts', 0)}，审计成功 {state.get('audited_successes', 0)}。累计数与当前回合数分开；心跳不计物理进展。

任务结果：

- 卧室门：door-0002 已独立审计成功；MuJoCo 派生无锁舌推门，不是解锁或Isaac。[公开结论](campaign/door-0002/public-review.json) · [封口连续视频](campaign/door-0002/video/episode.mp4)。
- 桌面苹果：{state.get('apple_status', 'apple-0001 策略进行中，尚无审计成功。')} 原苹果网格/初态保留；凸碰撞和0.18kg质量为明确适配。
- 冰箱策略及放入组合：尚未执行，不计成绩。冰箱独立候选保留原壳体空腔，闭门、净空、接触和站立工程校验已通过；[探针诊断](diagnostics/fridge-contact-001/report.json)不是机器人开门成绩。

下一步：{state['next_step']}

运行：actor `{state.get('actor_tmux', 'none')}`；唯一工程接续器 `rsi-ikea-continuation-0916`；零模型心跳每30秒读取状态。只有原进程退出、turn.completed 和新 state=continue 后才接续同一thread。

最新物理进展时间：{state.get('last_actual_progress_at', '未知')}。随后变化见 [actor-progress.json](actor-progress.json) 和 [网页进度](http://127.0.0.1:8765/#ikea-progress)；[heartbeat.json](heartbeat.json) 单列存活信息。

证据：动作/录像/冻结版本在 `campaign/`；只发布 [video-manifest.json](video-manifest.json) 中已封口视频。历史系统中断：{state.get('system_interruption', '无记录')}。

协作：{state.get('coordination', '未记录')}。队列、ACK、集成与跨任务验证分别记录。预算维护者已完成重启后发布；旧远端未知请求/费用仍保留，不查询费率余额。
'''
    if state.get('audited_successes') != 1:
        raise ValueError('Update task-result lines when a new task is audited successful')
    tmp = ROOT / 'STATUS.next.md'
    tmp.write_text(body)
    tmp.replace(old)
    print(json.dumps(dict(status_updated_from=now, previous_status=str(previous.relative_to(ROOT)))))


if __name__ == '__main__':
    main()
