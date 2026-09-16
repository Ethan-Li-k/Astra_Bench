# R018 任务 prompt 审查

用户强调：先检查自己的任务描述／prompt 是否充分，不把缓慢思考当失败；至少十次当前任务成功后进入 SIMPLE 推门。

## 明确任务

用任一 DEX3 手抓住图像中桌上的红色方块，使方块相对本回合初始高度上升至少 5 cm，并持续夹持至少 0.5 s，同时机器人保持站立。只依据 RGB、具名机器人状态和自己的实际尝试经验选择四点 ScaleBFM 动作；没有人工示范。闭手、腕部上升、推走方块或单张图像不等于成功。十次独立 reset 后的成功才解锁 SIMPLE 推门。

上述高度和时间是公开的任务要求，并非物体当前真值。物体坐标、接触力与隐藏 evaluator 状态仍不向策略开放。

## 当前 prompt 的具体不足与修正

旧 TASK 只有“Visually grasp the red cube, lift it clear of the table, and hold it steadily.”，没有给出可检验的抬升高度、保持时间和站立要求。主 skill 已说明反馈、夹爪语义、四点坐标和不能把闭合当抓取；问题不是完全没写流程，而是任务层要求不够具体。`tools/learn_grasp_skill.py` 的 TASK 已改为上面的明确版本。

当前运行进程已经加载旧 TASK，修改源文件不会热改这次推理。不得为声称 prompt 已改而中断正在运行的模型；其当前失败经验和 skill 自我修订仍需完整保存。下次安全启动将使用明确 TASK 与无推理时间上限的 adapter。

## 已补充给当前策略的明确任务

第2回合已通过本机 app-server 的正式 `turn/steer` 协议收到明确任务补充，而不是等待源码重启才生效。先读取本机生成的 TurnSteerParams schema，使用 expectedTurnId 前置条件绑定当前回合；本任务的临时 policy thread 不在 Codex app 可读线程列表中，因此向自有 app-server stdio 管道原子写入该协议请求。未调用 turn/interrupt，也未调用新的 turn/start。

请求与文字全文：`artifacts/R018/task-clarification-steer-request.json`；ack 在 episode-0002/app_server/rpc_out.jsonl，request id 为 `rsi-task-clarification-20260915-ep2`，返回原 turn `01a0a5fe-83fa-75f1-b3be-4b490e850a74`。内容仅补充任务要求、完整等待、保留经验和十次成功后推门；不含物体坐标、接触数据或回放结果，也没有替策略选择在线动作。下一版自改 skill 需要保留明确要求。

本回合多次动作的公开 reason 表明策略会撤回无证据的抓取判断、从手指与桌面的阻挡中改变方向、重新观察掉落方块。仍须等待完整回合和经验修订，再判断哪些反馈被保留，不能只看一帧或一次 timeout 归因。

下一步优先检查：下一版 skill 是否明确指间空隙与目标对齐、是否在接近时提前闭合导致推落、是否把 measured pose 与 reference 区分、是否把重复跟踪误差写成有证据的控制经验。具体在线动作由策略自己选择，开发侧不向它提供隐藏物体位置或预编好的成功轨迹。
