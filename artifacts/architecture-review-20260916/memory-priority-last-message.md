已完成[第二项修复候选](/home/galbot/lizekai/RSI/artifacts/architecture-review-20260916/memory-priority/FINAL.md)，**尚未合并**。

- 已复现真实审计否决记录被置顶的问题。
- 否决、未知、未完成或合同不匹配的记录不再作为成功优先项；后补审计在下一次检索生效，原经验保持不变。
- **18项检索测试＋8项原长度测试通过**，组合补丁兼容、快照无漂移。
- 已向SIMPLE既有inbox追加交接，仅queued，未ACK。等待唯一发布者集成及SIMPLE物理验证；未调用额外模型/API或运行仿真，不宣称物理收益。