# NT逐turn记录与审计兼容：交付

**候选未部署，在线文件和在途回合未改。** 已完成最新基线复现、最小三文件修复与联合验证。

- 复现：旧自动续接只保存 turn_002，漏掉 failed turn_001；旧auditor仍给完整审计成功。两条断言失败，原始日志/夹具保留。
- 修复：匹配的每个终态先按唯一编号/身份落盘，再允许续接；新 `codex-terminal-sequence-v1` 检查完整序列。写盘失败、缺号/重复/错身份、未恢复失败、最后未completed不能计完整成功。审计检索沿用同一结果，不改原生历史。
- **63/63离线测试通过**，含实际 run_episode 配假transport/backend、原权限/LearningHost/审计/经验回归。六个实际入口加runtime和新恢复提示均满足三项上限；无文本截断。
- 保留已上线的长度、审计检索、render-frustum及workspace-write/on-request/auto_review合同。publisher并发新增的auditor任务映射、库存刷新和进度文字已保留；最终diff零fuzz应用到本地副本成功，源码未覆盖。

[补丁](audit-compatible.patch)、[接入说明](INTEGRATION.md)、[测试回执](evidence/checks.json)、[最终漂移检查](evidence/drift-final.json)。仅交付唯一SIMPLE辅助publisher，排队结果见 [delivery-receipt.json](delivery-receipt.json)；排队≠ACK≠集成。

无模型/API/物理实验、环境修改或主账号调用。无进展重复断线仍由现有caller清理，重启现场丢失不能恢复；未声称持久保存或物理收益。API/IKEA不同调用链不可盲用。旧no-truncation结果保持原样。
