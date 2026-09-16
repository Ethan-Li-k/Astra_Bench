# SIMPLE 进展

更新时间：2026-09-16T12:36:57.298495+00:00
当前仅六类：XMovePick、BendPick、Handover、Mobile P&P、Grasp、XMoveBendPick。Grasp入口待澄清；IKEA/地面搬运暂停。旧91库存保留但不扩张。
后端：MuJoCo，推理期间物理暂停，非 RTC；推门是明确门框碰撞修复的 push-open 变体。

六类生效：2026-09-16T12:28:40.091351+00:00。以下总审计数含历史；新测评、切换时在途和历史基线分别计数，变体不合并。
XMovePick / xmovepick-campaign：历史 1成功/3尝试；切换在途 0成功/0尝试；生效后新回合 0成功/0尝试。
XMovePick / xmovepicksim-campaign：历史 1成功/1尝试；切换在途 0成功/0尝试；生效后新回合 0成功/0尝试。
BendPick / bendpick-campaign：历史 1成功/4尝试；切换在途 0成功/0尝试；生效后新回合 0成功/0尝试。
BendPick / bendpicksim-campaign：历史 0成功/1尝试；切换在途 0成功/1尝试；生效后新回合 0成功/0尝试。
Handover：入口澄清/验收准备中，未登记新回合成功。
Mobile P&P / mobilecheezit-campaign：历史 0成功/0尝试；切换在途 0成功/1尝试；生效后新回合 0成功/0尝试。
Grasp：入口澄清/验收准备中，未登记新回合成功。
XMoveBendPick / xmovebendpick-campaign：历史 0成功/2尝试；切换在途 0成功/1尝试；生效后新回合 0成功/0尝试。

- apple-campaign：审计成功 1/1；episode-0008，finished，117动作；终态分类 native_success。最近物理日志 2026-09-16T10:46:30.782288+00:00。
  成绩分层：自主 0；语义反馈辅助 1。
  已加载入口：790 words / 5883 chars / 5079非空白；组合SHA 432be7c09a525e00007a8c57183db16e33a49c9dafb39afa4e3c2588f19021d4。
  最近完整录像：artifacts/R019/apple-campaign/episode-0008/video/episode.mp4（历史物理录像，非直播）。
- bendpick-campaign：审计成功 1/1；episode-0006，finished，63动作；终态分类 native_success。最近物理日志 2026-09-16T07:17:55.310097+00:00。
  最近完整录像：artifacts/R019/bendpick-campaign/episode-0006/video/episode.mp4（历史物理录像，非直播）。
- bendpicksim-campaign：审计成功 0/1；episode-0002，等待模型/工具；物理暂停，31动作；终态分类 running。最近物理日志 2026-09-16T12:35:32.848608+00:00。
  已加载入口：766 words / 6122 chars / 5337非空白；组合SHA 9d438e685e4e1f2e4d0f344a9a03907230b23bb91a3fc5bec944d60a3cde005e。
  最近完整录像：artifacts/R019/bendpicksim-campaign/episode-0001/video/episode.mp4（历史物理录像，非直播）。
- boxplace-campaign：审计成功 1/1；episode-0004，finished，51动作；终态分类 verified_variant_success。最近物理日志 2026-09-16T10:22:34.617218+00:00。
  已加载入口：778 words / 5846 chars / 5054非空白；组合SHA 1f196bac4cfbc4f9ab5fc94563e470e66f5c09de63121186356a864e32259d46。
  最近完整录像：artifacts/R019/boxplace-campaign/episode-0004/video/episode.mp4（历史物理录像，非直播）。
- chair-campaign：审计成功 1/1；episode-0001，finished，38动作；终态分类 native_success。最近物理日志 2026-09-16T10:59:40.125327+00:00。
  已加载入口：774 words / 5986 chars / 5200非空白；组合SHA 1b8e872cd24079da29a8933982c6f9fcbbc3092c08fa3d3d1d1ed6b320c3c3c5。
  最近完整录像：artifacts/R019/chair-campaign/episode-0001/video/episode.mp4（历史物理录像，非直播）。
- closedoor-campaign：审计成功 1/1；episode-0001，finished，41动作；终态分类 verified_variant_success。最近物理日志 2026-09-16T12:19:23.122560+00:00。
  已加载入口：776 words / 6006 chars / 5218非空白；组合SHA 8bb0e49c22ac7e85703c278aab0225bcbc0c511c4258ec87485087c0be6f430e。
  最近完整录像：artifacts/R019/closedoor-campaign/episode-0001/video/episode.mp4（历史物理录像，非直播）。
- door-campaign：审计成功 10/10；episode-0020，finished，39动作；终态分类 verified_variant_success。最近物理日志 2026-09-16T11:23:40.875397+00:00。
  已加载入口：828 words / 6192 chars / 5350非空白；组合SHA d0b6d482ef62a8f1a911695e84be73c0c02cbcb05f360eb2d3096e9edde9ef53。
  最近完整录像：artifacts/R019/door-campaign/episode-0020/video/episode.mp4（历史物理录像，非直播）。
- faucet-campaign：审计成功 1/1；episode-0008，finished，11动作；终态分类 native_success。最近物理日志 2026-09-16T10:06:22.445171+00:00。
  已加载入口：789 words / 5893 chars / 5090非空白；组合SHA 0566e81ae00914db59844522201eeb615b11a3ebd12fd69087724453d41a8e48。
  最近完整录像：artifacts/R019/faucet-campaign/episode-0008/video/episode.mp4（历史物理录像，非直播）。
- mobilecheezit-campaign：审计成功 0/1；episode-0001，等待模型/工具；物理暂停，44动作；终态分类 running。最近物理日志 2026-09-16T12:36:44.016611+00:00。
  已加载入口：776 words / 6006 chars / 5218非空白；组合SHA 8bb0e49c22ac7e85703c278aab0225bcbc0c511c4258ec87485087c0be6f430e。
- oven-campaign：审计成功 1/1；episode-0001，finished，14动作；终态分类 native_success。最近物理日志 2026-09-16T10:23:09.166220+00:00。
  已加载入口：774 words / 5986 chars / 5200非空白；组合SHA 1b8e872cd24079da29a8933982c6f9fcbbc3092c08fa3d3d1d1ed6b320c3c3c5。
  最近完整录像：artifacts/R019/oven-campaign/episode-0001/video/episode.mp4（历史物理录像，非直播）。
- trashcan-campaign：审计成功 1/1；episode-0001，finished，5动作；终态分类 native_success。最近物理日志 2026-09-16T10:35:44.609257+00:00。
  已加载入口：774 words / 5986 chars / 5200非空白；组合SHA 1b8e872cd24079da29a8933982c6f9fcbbc3092c08fa3d3d1d1ed6b320c3c3c5。
  最近完整录像：artifacts/R019/trashcan-campaign/episode-0001/video/episode.mp4（历史物理录像，非直播）。
- xmovebendpick-campaign：审计成功 0/1；episode-0003，等待模型/工具；物理暂停，18动作；终态分类 running。最近物理日志 2026-09-16T12:36:22.551610+00:00。
  已加载入口：751 words / 6101 chars / 5332非空白；组合SHA e7e66f01e1ad4c59d12935ac923fb8e232502b35befcbdef78ddedf00e7c395b。
  最近完整录像：artifacts/R019/xmovebendpick-campaign/episode-0002/video/episode.mp4（历史物理录像，非直播）。
- xmovepick-campaign：审计成功 1/1；episode-0003，finished，31动作；终态分类 native_success。最近物理日志 2026-09-16T12:07:36.166526+00:00。
  成绩分层：自主 0；语义反馈辅助 1。
  已加载入口：809 words / 6164 chars / 5340非空白；组合SHA e8974a8b9aa2f1ec61cca912eaba4ab84b0adaebb45f91d39e20cdec2696d5b4。
  最近完整录像：artifacts/R019/xmovepick-campaign/episode-0003/video/episode.mp4（历史物理录像，非直播）。
- xmovepicksim-campaign：审计成功 1/1；episode-0001，finished，38动作；终态分类 native_success。最近物理日志 2026-09-16T11:55:09.342489+00:00。
  已加载入口：776 words / 6006 chars / 5218非空白；组合SHA 8bb0e49c22ac7e85703c278aab0225bcbc0c511c4258ec87485087c0be6f430e。
  最近完整录像：artifacts/R019/xmovepicksim-campaign/episode-0001/video/episode.mp4（历史物理录像，非直播）。

重启恢复：door15旧boot中断，61动作、无完整turn/result/skill_update；MP4缺moov保留，不冒称可播放。证据 recovery-20260916/door15-interruption.json。
框架：ARCH长度与MEMORY-PRIORITY、相机render-frustum-v1已在门16和水龙头8完成真实调用链及受限skill_update验证，证据instruction-cap-integration/status.json。NT逐turn记录/审计兼容候选已发布，63项针对检查通过，门19完整单turn及修订真实验证；尚未发生真实网络恢复。证据nt-audit-integration-20260916/status.json；共同变更不能作单因收益归因。
下一步：完整等待各活动回合，逐轮审查；后续仅按最新授权六类安排，不扩张旧库存，不重复凑推门数。推门历史10次门槛凭door-campaign/ten-success-milestone.json核验。苹果H001004先张手包络后闭合。权限修复首次生效门18/垃圾桶1/办公椅1，实际workspaceWrite/on-request+auto_review已随真实动作核验；旧在途不热改，证据recovery-20260916/permission-physical-route-verification.json。
失败分层：预算截断、系统中断、提前终止均不凑三次自主物理失败求助。入口/标定/检索并变不能作单变量因果结论。
来源：各任务memory/versions、公开rollout、独立host审计；共享core未晋升。91入口库存保留，预检和未尝试不计成功。
范围：本主管仅SIMPLE；IKEA/地面搬运按用户暂停，由原owner保留收尾证据。视频页 http://127.0.0.1:8765/ 读取既有证据。

机器人本体观测：ROBOT-STABILITY-OBS-V1 状态 published_first_formal_episode_audited_success；首次新回合 xmovepick-campaign/episode-0003。仅新增命名骨盆测量/动作内采样摘要，未改控制或安全阈值；单因任务收益未隔离验证。证据 artifacts/R019/robot-stability-integration-20260916/status.json。
