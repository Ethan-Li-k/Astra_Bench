> 2026-09-16 门框修复登记更新：旧schema 1保留；新schema 2明确 `original_physics=false`，严格绑定唯一四box修复及证据。精确格式、未签发草稿和主控命令见 [新版格式](../../artifacts/R020/frame-override-receipt-format.md)。物理检查使用 `check --physical-only`，登记使用 `enroll --receipt ... --physical-only`；不涉及API或费用。0010/0011已完成主控审计与本次离线预检，仍待主控签发登记收据；0012未计入。本页下方“初始0”等为旧交付时点，当前登记数见 physical-gate-state.json。

# R020：独立协调入口

仅使用 Python 标准库和已有 ffprobe；无网络、无模型调用、无仿真启动、无 API 凭据读取。全部状态写入 `artifacts/R020`。SIMPLE 由既有 supervisor 继续。

## 检查、等待、恢复

```bash
cd /home/galbot/lizekai/RSI
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/ikea_gate.py check
```

持续等待已在独立 tmux `rsi-r020-coordination-wait` 运行；先 `tmux has-session -t rsi-r020-coordination-wait`，仅在它不存在且无现存 waiter 时恢复：

```bash
tmux new-session -d -s rsi-r020-coordination-wait \
  'bash /home/galbot/lizekai/RSI/tools/coordination/run_waiter.sh'
```

wait 每60秒核验一次，tee 追加 `waiter.log`，进程文件锁拒绝重复 waiter。只在状态变化时打印；无需主账号或模型轮询。异常配置转为 `invalid_configuration`；证据改变会重新拒绝，不保存粘性的“已解锁”。进程中断后从输入 registry 重算，输出用临时文件+fsync+replace；不会重复发消息或重复动作。工作区沙箱/自动审批保持原配置，waiter 仅执行本地检查。

## 真实 host 登记

生产根固定为 `artifacts/R019/door-campaign/episode-NNNN`，不发现文件并自动计数，不读取未登记的大量轨迹。`host-audits.json` 初始为空；当前真实成功为0。

既有 supervisor 在**真实完整成功之后**独立检查原启动记录、进程身份、独立 reset、正式初态、唯一动作写入者与原物理配置。将自己的来源审查保存在 RSI/artifacts 内，把 `host-receipt.template.json` 复制到 R020/host-receipts 的新文件，填写实际值与 evidence SHA256，不能补造缺失记录、从失败自述生成 success、从 ep 目录名推断已 reset。`data_kind` 只有已审查真实来源才设为 `real_physics`；保留旧收据与失败证据。

- `reset.launch` 是原 host 的 boot ID、PID、启动 ticks；同 PID 重用由 boot/start 区分。当前适配器要求一个正式 runner 进程一个回合，同进程新机制要单独审查后升级 contract。
- `host_evidence` 引用 RSI 内 artifacts 文件，路径相对 RSI；应包括真实启动/重置证据和 supervisor 审查记录，其哈希绑定原始记录。不能只写一句“已成功”。
- `runtime_source_sha256` 复制并核验该回合 render manifest 的原始代码哈希。来源 review 需核对 evaluator、初态、资产和控制器没有更改任务语义；哈希相等本身不是语义审查。
- `evidence_sha256` 必含 result、全部完成的 `turn_NNN.json`、SKILL、trace、manifest、scene_setup、原始 episode.mp4。不能用 Isaac 重渲染替换原始物理录像。

填写后零模型登记：

```bash
python3 tools/coordination/ikea_gate.py enroll --receipt host-receipts/<真实收据文件>.json
```

该命令先完整校验且新增一个不重复成功才原子登记；同一收据重跑不重复记数。check 会再次串流该候选 trace，重算从闭门初态开始的手接触、开角30°、连续1秒、站立、连续50Hz记录、完整终态、实际动作数和完整25fps录像，核对推理与修订结束。frame/tick/路径/哈希不能替代 host 来源审查。任何缺项均拒绝。

**信任边界**：这是可信 host 记录与文件内容的审计器，不是能证明任意文件来自真实物理的密码学鉴伪器。actor 不得写 registry/receipts；同一 Unix 用户的恶意伪造者不在此组件可独立防护的范围内。原 runner 未提供独立 provenance 时，不计数，留待 supervisor 补足真实可核实证据。当前实现适配 MuJoCo 正式 asset003 push-open，未支持的 Isaac 物理/新 controller contract 需单独验证，不能静默放行。

## 已授权共享预算；来源和计费待核实

唯一授权源为 `ref/tasks/api-budget.json`：全任务所有角色/环境/分支累计硬上限10000元，累计每1500元汇报，达到上限最终汇报；汇报不重置/追加授权。门槛直接读取该文件，不要求用户重复授权。`api-configuration.json` schema 2 只存提供方、模型费率、计费币种、整数货币单位、价格版本/有效期、换算上界依据和费用上界实施证据；这些来源字段目前为空/未验证，不能猜价格，也不保存或读取凭据。

`shared_budget.py` 是离线账本库，默认固定 `artifacts/R020/shared-budget-ledger.json`，CNY整数分。初始化已完成，真实已结算0分、在途预留0分。查看：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/shared_budget.py status
```

`init` 只可创建不存在的账本，既有账本不会被重置；损坏账本/预算条款不一致会拒绝。稳定的旁路文件锁包住读-校验-更新，JSON临时写入、fsync、原子替换并同步目录。同主机的所有并发调用必须使用这一账本；远端执行器必须接入同一权威账本，不能复制账本到每个环境各算10000元。跨主机接入尚未实施/验证。

未来适配顺序（当前没有任何网络/API执行实现）：

1. 执行器核验最新IKEA物理门槛及来源/计费配置。用唯一 request_id 和角色/环境/分支身份调用 `BudgetLedger.reserve(request_id, scope, maxima)`；maxima必须覆盖所有计费组件、费用、重试和换算的可强制最大值。按真实已验证单价与换算上界整数运算并向上取整。`已结算 + 所有未结算预留 + 本次最坏费用 <= 1000000分` 才能持久化预留。未知/无界费用拒绝，缺提供方/单价/币种/换算证据或上界实施证据拒绝。
2. 完成预留后，发请求**之前**调用 `begin(request_id)`。仅 `transitioned=true` 是首次进入在途；重复调用返回false，不能据此重发。`reserve` 重复同ID和同参数返回原记录，不再次占额；参数冲突拒绝，取消/已结算ID不重新启用。提供方重试/幂等ID对接仍待验证。
3. `settle(request_id, billing_ref)` 要有确定的逐请求最终账单证据（路径、哈希、提供方、模型、账单事件ID、实际CNY分与换算依据）；同一证据重复结算不重扣，冲突结算拒绝。未完成账单不能释放额度。实际费用超过先前上界时如实保留并冻结后续预留/发出，不能截断费用掩盖超支；这表示将来的接口保证失效，需对账。离线账本无法替代提供方最大费用强制实施。
4. `cancel` 只允许尚未 `begin` 的预留，并保存原因；在途/已结算不可取消。超时、进程崩溃和价格到期不会自动释放在途占额。若确认实际零收费，也必须有最终账单证据才能结算为零。
5. 每跨越150000分阈值生成唯一持久化pending事件；单次结算跨多个阈值逐个保存，最终1000000分也保存事件。重复结算/查看/重启不重复提醒或删事件。真正向用户汇报累计/剩余额度、进度、独立成功数和失败结论之后，才可用可核实发送记录调用 `acknowledge_report(threshold_fen, delivery_ref)`；排队/草稿/工具回显不能标reported。账本本身不发送消息、不因reported增加预算。

计费与报告证据路径只能在 RSI/artifacts，哈希绑定内容；证据真实性仍由可信host/未来适配器核对。测试来源/费用/发送证明均明确标记synthetic，生产拒绝其混入。当前只完成离线并发账本验证，没有验证任何真实API请求、计费或跨主机runtime。

门槛状态：不足3次 → `waiting_simple_successes`；3次但来源/计费/上界实施配置缺失 → `waiting_api_configuration`；账本不可用 → 不登记可启动。条件齐备也仅 `eligible_registered_only`，不花费或发请求。来源未知不阻塞第二账号套餐下SIMPLE。

## supervisor 交接

通过第二账号 `run.sh queue --thread 01a0a867-d7aa-71f2-8547-e264d6d09ede` 的正规通道排队；inbox 和回执分别是 `supervisor-inbox.md`、`queue-receipt.txt`。未发送 tmux 按键，未写内部 session，未修改进程或 runner。

`delivery_status.py` 已从新公开 `item.completed / agent_message` 验出完整 `R020-PARALLEL-SKILLS-20260916 ACK — 已读新增要求及预算文件…`，并再次核对原日志字节偏移与事件SHA256；见 `ack-verification.json`。工具回显、旧ACK和queue回执不算已读。未重复发送同一消息。R020 waiter仅check/登记/ACK，不负责resume；主控自然结束接续由既有 `rsi-simple-continuation-0916` / `codex-account-2/continuation/watch.py` 独占，禁止另建resume watcher或并发resume。

## 验证与测试隔离

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/test_ikea_gate.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/test_delivery_status.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/test_shared_budget.py
```

先拒绝失败/重复/缺证据/回放等样本，最后检查三个合成正例计数及 API 等待。所有夹具留在 R020/synthetic-tests，含明确 SYNTHETIC 标记；测试使用可注入的视频元数据桩。它们不是物理尝试、真实 host 成功或录像鉴真测试，不写生产 ledger。生产 CLI 无覆盖根目录/跳过审计参数；显式 synthetic receipt 即便复制到生产根也拒绝。

源代码与测试记录见 coordination-status.json。Canvas 是静态评审快照，当前可恢复状态以 JSON 为准。

本轮事实修正前文件保存于 R020/history，标注旧预算/ACK陈述已被取代。共同核心只由SIMPLE supervisor发布；ground-to-table保持独立写域，本线程不写该域或公共skill。角色设计直接复用已有报告。
