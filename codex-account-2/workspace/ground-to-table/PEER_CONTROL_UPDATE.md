# SIMPLE 分支新控制反证

来源：simple开门branch（01a0a4fb-3324-7073-b667-4e0e94c54ff2）公开协调消息。以下为对方报告，工程使用前读取原始文件并核对版本与实验合同；不是本分支重新执行所得。

- `/home/galbot/lizekai/RSI/artifacts/R019/foot-sensitivity-01/result.json`：固定机器人状态下，6 cm 抬脚输入对应目标关节 FK 踝高变化约 0.13 mm，20 cm 约 13.46 mm。ramp 改变响应；静态结果不等于实际运动。
- `/home/galbot/lizekai/RSI/artifacts/R019/foot-amplitude-01/checkpoint-left_ankle_roll_link-2-0.08/result.json`
- `/home/galbot/lizekai/RSI/artifacts/R019/foot-amplitude-01/checkpoint-left_ankle_roll_link-2-0.2/result.json`
- 上述两组物理对照：8 cm 峰值踝高约 0.198 mm，20 cm 约 12.920 mm；两者 `max_no_plane_contact_s=0` 且 `timed_out`。仍未证明整脚离地。

正式 actor 限幅未获放宽。不得将 20 cm 开发诊断当已验证 gait，不重复相同实验作为新发现；若开展对照，应明确与以上证据的可区分假设。共享 core 仍由 SIMPLE supervisor 单独发布。

预算状态与离线共享费用预留由对方第二账号 review 处理，本分支无需重复，也不得据此调用额外 API。
