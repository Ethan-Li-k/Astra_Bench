---
name: loco-manip-direct
description: Learn native faucet operation through public visual evidence.
---

## Shared control methods

Use gpt-6-astra/xhigh. Read workspace.json, its task_specification, assembled SKILL.md and experience_read. Preserve the original task and native criterion; history supplies candidates, never a replacement objective. Use only campaign public evidence, named robot state, camera calibration, robot geometry and explicitly listed transferred_self_experience. No human demonstrations, hidden object/contact/evaluator state, other simulators, runtime inspection or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect both RGB views, calibration, measured/reference poses, joints, gripper closure and current finger mesh bounds. Before acting call experience_select with source IDs, rationale, adaptation and rejected reuse; reselect when failure mode changes. Retrieve relevant versions and cited trajectories selectively. Preserve concise decisions, tool feedback, uncertainties and next hypotheses.

Transfer grasp437/438's retrieve-test-observe-correct procedure, not cube coordinates, capsule geometry, closure fractions, table plane or orientation. Ten grasp successes, including five endpoint-retained successes, establish neither locomotion nor faucet transfer.

Review one waypoint using the latest observation and a unique request ID. Explain observed evidence, purpose and expected visible change. Include all four absolute world poses in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect current per-link translation limits, 0.10rad rotation and 0.5–3s duration. Never output q29 or torques. Geometry tools calculate; scalebfm_act executes. Grippers are ramped closure fractions, zero open and one closed, not force or aperture measurements. Wrist frames are not calibrated TCPs.

After each blocking action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. A timeout, target_reached, closure or pixel overlap establishes no grasp or lever motion. Change a justified variable after failure; avoid repeated unchanged commands and biased measured anchors. Await complete service/model responses; reasoning pauses simulation.

Triangulate reliable stereo correspondences using calibrated conventions and verify reprojections. Ray-plane projection is not depth. Reject shadows, occlusions and mismatched silhouette endpoints. Check clearance of the entire hand. Use a short physical probe and independent observation to test the task relationship. Preserve disagreement between views.

Monitor feet even when inactive. Uncommanded foot displacement requires withdrawal and reassessment. Current measured support holds are candidates, not guarantees of stability. Never command old anchors beyond limits after slipping.

Stop physical actions on rollout_finished, regardless of generic next_call or raw in_progress. After at least three actions, finish_attempt may end an evidenced stall with a changed hypothesis; it is not success. Do not consume budget through idle holds. After termination submit a complete revised local skill, concise lesson/change_summary and existing episode public evidence paths. Respect length caps. Shared candidates require cross-task validation and grasp regression; local updates never overwrite the shared core.

## Task-specific faucet evidence

Objective: move the small water-control lever beyond 0.7rad and satisfy native accumulation while stable. Host outcome determines success. There is no door-style one-second criterion. Report visible retention separately.

Episode0001 exhausted 74 actions without verified lever rotation/grasp. Side approaches and local-X rolls tracked but were not opening procedures; closure .20–.50 did not establish retention. Support slipped during constrained approaches. Preserve moving-part identity and pivot uncertainty.

Episode0003 ended policy_declared_stall after 14 actions, 12 target_reached and 2 timed_out; no verified opening/grasp. Left free-space lifts 1–7 tracked with steady feet. Active attitude hold 8 had <2mm position error but 0.279rad attitude error. Recompute finger clearance from actual orientation; position tracking does not imply attitude tracking.

Initial matching white silhouette rows 185–210 reconstructed a near-horizontal plate around z .881–.883m. These are episode-local analysis estimates, not reusable coordinates. Coarse endpoint disparities biased height. Finger bounds after 12 placed the middle tip near the plate's top, explaining why upward probing could miss. Neither plate identity nor contact was established.

Upward 10 and lateral 11 probes showed no identifiable relative motion; withdrawal 12 restored visibility. Lower insertion 13 caused 108/83mm left/right foot displacement despite support targets. Withdrawal 14 with current measured support anchors was followed by <0.1mm foot displacement. This does not prove contact or anchor causality. Do not repeat this insertion.

Next hypothesis: obtain an unobstructed oblique view distinguishing the small control from the broad plate/spout, verify attitude response in free space and validate a changed contact before probing. After two no-motion tests withdraw and revise the contact model.

Local orchestration errors executed no physics: unavailable structuredClone, non-async eval and truncated crop encoding. A 30.03mm proposal was rejected; retrying its output directory was also rejected. Read explicit no_execution receipts, then use a valid bounded step, fresh output directory and request ID; never replay uncertain execution.
