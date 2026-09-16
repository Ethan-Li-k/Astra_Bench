# 固定门框修复登记：schema 2

仅支持 `asset003-exact-frame-four-boxes-v1`，source mesh SHA256 必须为 `bd01dac54cb36a782dcb5d589cc7b8e4faaaffff6ecd4ade70358ee8a50679a1`。这是明确改变固定门框碰撞表示的推门变体，**不是原样 native CloseDoor benchmark**。旧 schema 1 / `host-receipt.template.json` 原样保留，只接受未启用 frame override 的旧碰撞设置。

完整新格式在 `host-receipt.frame-override-v2.template.json`。审查固定配置为 `approved-door-frame-override-v1.json`，其 SHA256 已钉入 checker：`f8335b5ad280fac9a3576bd8b17a3e6a594d0e5e25387070565273df9687f53f`。批准文件固定完整四 box 几何、原source路径与SHA、保留属性，以及原/修复对照、碰撞审查、实现和测试六份证据SHA。任何缺项、未知ID、几何/哈希改变都拒绝；不会在运行时自动重新批准。

与 schema 1 的精确差异：

- `schema=2`；已由主控复核签发时才 `data_kind="real_physics"`。
- `provenance_review` 恰为以下布尔字段：`independent_reset=true`、`full_episode=true`、`no_replay=true`、`no_diagnostic_initial_state=true`、`single_action_writer=true`、`original_physics=false`、`reviewed_physics_revision=true`。**不要将 original_physics 改为 true**。
- `physics_revision` 精确复制新版模板：override id、source mesh SHA、批准文件相对路径与固定SHA、`unmodified_native_benchmark=false`、六项 `preserved_properties`。其中惯量/活动叶片把手铰链/接触参数保留的依据是已冻结审查与原测试，不要求重新启动仿真。
- `reset` 完整复制并核实该回合 `video/scene_setup.json.reset_provenance`；必须与 `success_review.json.reset` 一致。seed、reset id、boot/PID/start ticks 独立性继续检查。
- `host_evidence` 至少包含该回合 `success_review.json` 与 `video/scene_setup.json` 的 RSI 相对路径和SHA；主控可补充原始启动/唯一写入者证明。收据仍只能由既有主控签发，R020不代签。
- `evidence_sha256` 包含原来全部必需证据、完整所有 `turn_NNN.json`，另含 `success_review.json`、`account_route_verified.json` 和该success review引用的每个证据文件。完整turn、SKILL、结果、原录像与trace重核不变。
- `runtime_source_sha256` 与原manifest完整一致，其中 `rsi/simple_door_collision.py` 必须等于已审查实现SHA。

## 主控可直接使用的未签发草稿

`frame-override-validation/episode-0010.UNSIGNED.json` 与 `episode-0011.UNSIGNED.json` 已从现有真实证据填充路径、reset事实、版本和哈希；`data_kind` 仍为 `unpopulated_template`，所有需主控确认的provenance字段仍为false，**不能登记**。没有伪签任何成功来源。相应 `.preflight.json` 是离线证据预检，不是收据。

需要重新生成/核对未签发草稿时（幂等，不登记；已有不同草稿拒绝覆盖）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/frame_receipt.py --episode episode-0010
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/frame_receipt.py --episode episode-0011
```

主控在独立核实来源后，复制草稿为新文件（勿覆盖原草稿或旧收据），填写上述主控确认项：

```bash
mkdir -p artifacts/R020/host-receipts
cp -n artifacts/R020/frame-override-validation/episode-0010.UNSIGNED.json artifacts/R020/host-receipts/episode-0010.frame-v2.json
cp -n artifacts/R020/frame-override-validation/episode-0011.UNSIGNED.json artifacts/R020/host-receipts/episode-0011.frame-v2.json
```

**仅主控完成签发后**执行下列命令。它们只做物理登记，不读取API配置或费用，不启动IKEA：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/ikea_gate.py enroll --receipt host-receipts/episode-0010.frame-v2.json --physical-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/ikea_gate.py enroll --receipt host-receipts/episode-0011.frame-v2.json --physical-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/coordination/ikea_gate.py check --physical-only
```

同收据幂等、重复reset/process/trace/video拒绝。2次仍不能通过，3次合格收据后只输出 `physical_gate_registered_only`，无任何自动探索或模型调用。状态在 `physical-gate-state.json` / `coordination-status.json.physical_gate`；既有零模型waiter已切换physical-only并重载，没有新增watcher或resume。

本次只读预检0010/0011：分别3343/5252 ticks、18/28 actions、1672/2626原录像帧；接触/30度/1秒/站立通过，重算与原host review一致。0012未检查、未计数。生产registry保持本次维护前内容，当前未登记不等于主控没有真实成功。真实v2 enrollment仍待主控签发；本次41项测试（19项新schema、22项既有gate）用隔离合成夹具，不构成真实物理成功。
