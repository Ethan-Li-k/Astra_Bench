当前问题：实际网页把 door-0001 策略录像标成工程诊断，并无依据地称原始 USD 场景带锁舌。
总目标：只修复已复现的两个文案/分类问题，保留正常进度、反馈和录像播放，不影响机器人。
不可重犯的错误：不并发修改共享 UI；不把宿主记录异常归为物理失败；不把诊断当策略成绩；不用主账号模型。

你仍是唯一网页发布者 01a0a980-7943-7963-9f36-b9c43c90c2da。根任务已通过辅助 queue 发两次缺陷报告，但上轮结束时若仍未修复，请现在只做这项定向修复。先阅读 human-feedback/dashboard-upgrade/REVIEW-IKEA-VIDEO-KIND.md、ikea/web-progress-verification/ROOT-CUA-QA.md，以及实际 ikea/video-manifest.json。不要重新设计界面或跑新模型/机器人。

按 manifest category/kind 区分 diagnostic 与 learning/policy_incomplete；door-0001 为12动作后宿主记录异常中断的真实策略尝试，未完成/未审计成功。完整录像是已封口的连续记录，不代表任务成功或回合完整完成。保留诊断录像不计策略成绩。原始 USD 是否有锁舌未证实，改为“不等同原始 USD 场景完整物理验证”，不要反向断言原场景无锁舌。

验收：一个工程诊断视频与一个 policy_incomplete 视频的针对性回归；仅重启网页服务；实际网页显示正确分类、成功数不增加；保留原视频/原始回执。必要时沿用已完成的其他测试证据，不重复整套无关测试。回执写 human-feedback/dashboard-upgrade/IKEA-LABEL-FIX.json，说明部署时间、改动、验证结果。不修改其他任务负责人映射，本项由其主控继续处理。
