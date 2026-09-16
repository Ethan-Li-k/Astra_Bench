# 新批次接口（2026-09-16）

预算库已经发布到 `tools/coordination/shared_budget.py`；SHA256见deployment.json。此前“ground002仍在途，等待自然结束”被已核验的主机重启取代。服务端请求及实际费用仍可能未知，所有旧hold继续保留。旧call55不能重发，也不能补造completion。

`batch-terms.example.json`仅提供字段示例，不是已登记批次。owner为真实新run选择唯一batch_id，去掉example_only，加入新episode/skill/公开信息包引用及适用范围；额外字段也全部进入哈希。不要改ground001/002的任何原文件。

新batch的schema=2，branch为ikea/api-ground-to-table/simple，model=gpt-6-astra、reasoning_effort=xhigh。provider/destination固定现有gateway与/v1/responses，最多120 calls、2000000 payload bytes、16384 output tokens；输入字节上限不是token上界。校准来源/尺寸/倍数必须沿用实际记录，不虚构费率。pricing_verified与hard_cost_bound保持false，automatic_retries=false，new_observation_data_authorized=true，data_scope=actor_public_rgb_robot_state_actions_skill。这些字段是当前用户任务的工程化范围约束，不声称用户逐字批准此schema。

生成只读登记文件的命令（由分支owner提供实际terms；不会写账本或发请求）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 ikea/budget-coordination/register_batch.py \
  --terms ikea/OWNER-NEW-BATCH-TERMS.json --name ikea-NEW-UNIQUE-ID \
  --retain-legacy artifacts/R021/api-ground-001/batch.json \
  --retain-legacy artifacts/R021/api-ground-002/batch.json
```

输出 `ikea/budget-coordination/approvals/<name>/{batch,approval,registration}.json`，含精确path/sha256；存在同名目录立即拒绝。invalid输入留下文件但无成功registration，不允许消费。approval schema2通过authority锁定真实授权文件SHA和桌面session；provenance=engineering_translation_of_user_task，user_approved_this_schema=false，没有虚构user_quote。members将batch除approval引用之外的完整字典用现有fingerprint绑定，避免循环哈希。authority文档改动必须重新审查；不能自动跟随新SHA。

同一明确授权组 `rsi-20260916-ikea-parallel-v1` 的不同有效approval可并行，不要求两个owner同时改一份审批文件。每份审批只绑定自己实际新批次；不提前批准未知未来模型或数据范围。未列出的旧批次/无batch的hold仍拒绝；retained_legacy_batches仅允许其未知占额共存，不授予旧请求重试权，不要求把重启中断伪造为completed。

分支adapter仍使用现有 `reserve(meta) -> reservation`、`settle(reservation, receipt)` 传输合同；共享库的 `reserve_empirical(plan_ref)` / `begin_empirical(request_id,payload_sha256)` 返回值不变。owner只在自己的新adapter里登记新run与approval路径；ground旧hook/actor硬编码的注册列表和run限制没有被本维护任务修改。schema2即使<=6 calls也必须提供call_index。scope.branch必须匹配batch.branch，计划的校准尺寸/倍数须与batch一致。

call ID严格为 `<batch_id>-call-01` 起连续增加，取消的未发送slot也不能复用。精确计划/payload哈希不能换；begin的transitioned只有首次true，false或任何异常都不得发送。先持久化inflight后发请求；故障/超时/结果未知留hold，不重发。同batch下一call必须有原有合格完成证据；别的明确授权分支可继续，但所有旧/新预留共同占用全局额度。completed不等于settled，usage不等于账单。

部署时已用原actor ResponsesSession与原hook做真实接口、假网络返回的兼容测试。新增IKEA/ground恢复adapter须自行验证注册、数据授权和返回模型约束；真实付费API运行尚未由本任务验证。所有实际发送交由分支owner，不由登记命令执行。
