已上线，ready=true。页面：http://127.0.0.1:8765/#framework 。部署时间：2026-09-16T11:53:33.524441+00:00；网页 PID 1139523，原 tmux + tee 服务继续运行。

仅修改 `dashboard.py` 的 `stability_observation`。兼容真实 `status=candidate_only`、无 ready 的回执：固定候选 `ROBOT-STABILITY-OBS-V1` 与同目录 progress 的 `bounded_delivery_complete`、双端明确已排队/未集成组合共同确认交付。实际 progress 未提供 candidate_id；若提供则必须匹配。未知 ID、缺阶段、交接不明或集成状态冲突均不判定完成；原 ready 格式继续兼容。

实际网页显示“候选已交付；待发布者审查集成”。当前问题/下一步已替换较旧管理描述，说明候选完成、等待唯一发布者自然边界检查与集成，未部署/物理收益未验证。交接已排队与负责人尚未确认分别表述。NT 已发布、门19已加载、真实断线恢复未验证及其他里程碑保持原样。

验证证据：

- 复用原12项fixture并增加1项真实格式回归（含10种不完整/冲突组合）；修复前13项中仅新增项失败，修复后13项全部通过。日志：`tests-before.log`、`tests-after.log`；旧投影：`actual-schema-before.json`。
- 实际8765仅做3项框架相关浏览器检查，全部通过，见 `browser-results.json`。[页面截图](production-framework.png)已读取确认。
- `preservation-after.json` 确认仅一个函数的 AST 改变，其他 UI/反馈/媒体文件、原候选三份回执哈希不变。备份和差异见 `backup-manifest.json`、`changes.patch`。
- 身份核验及唯一UI重启见 `restart-before.json`、`restart-after.json`、`final-health.json`。没有模型/API/物理调用，没有对外queue或表单提交。

候选仍待原唯一发布者处理；本轮没有部署候选或研究机器人实现。完整机器回执见 `result.json`。
