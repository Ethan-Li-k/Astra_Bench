
## 全局模型与 RSI 迭代约束（2026-09-15 用户追加）

- 始终使用 `gpt-6-astra`，推理强度 `xhigh`；禁止自动切换其他模型或降低强度。
- RSI 当前授权从自行执行的轨迹获取经验、跨尝试读取经验并自我修改 loco-manip skill。先累计 10 次独立重置后的真实物理抓取，再进入 SIMPLE；单次失败不代表任务结束。仍不上真机。
- 主 harness/skill 长度以 `/home/galbot/lizekai/RSI/GPT-as-Policy` 最大 SKILL.md 为上限，每次修改都校验并保存版本与证据。冻结测评与技能学习分开记录。
