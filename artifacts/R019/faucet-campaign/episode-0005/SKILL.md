---
name: loco-manip-direct
description: Learn native faucet operation through public visual evidence.
---

## Shared control methods

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Preserve the original task and native criterion; history supplies candidates, never a replacement objective. Use only campaign public evidence, named robot state, camera calibration, robot geometry and explicitly listed transferred_self_experience. No human demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect both RGB views, calibration, measured/reference poses, joints, gripper closure and current finger mesh bounds. Before acting call experience_select with source IDs, rationale, adaptation and rejected reuse; reselect when failure mode changes. Retrieve cited evidence selectively; record decisions and uncertainty.

Transfer grasp437/438's retrieve-test-observe-correct procedure, not coordinates, geometry, closure, plane or orientation. Ten grasp successes do not establish locomotion or faucet transfer.

Review one waypoint from the latest observation with a unique request ID. Explain observed evidence, purpose and expected visible change. Include all four absolute world poses in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect current per-link translation limits, 0.10rad rotation and 0.5–3s duration. Never output q29 or torques. Geometry tools calculate; scalebfm_act executes. Closure fractions are ramped commands, zero open and one closed, not force/aperture measurements. Wrist frames are not calibrated TCPs.

After each blocking action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Timeout, target_reached, closure or pixel overlap establishes neither grasp nor lever motion. Change a justified variable after failure; avoid unchanged retries and accumulated biased measured anchors. Await complete service/model responses; reasoning pauses simulation.

Triangulate reliable stereo correspondences using calibrated conventions and verify reprojections. Epipolar agreement alone cannot establish correspondence or moving-part identity. Ray-plane projection is not depth. Reject shadows, occlusions and mismatched silhouette endpoints. Transform current finger bounds using actual attitude; bounding-box overlap is not contact. Check whole-hand clearance. Use a short probe and independent observation to test the task relationship, preserving disagreement between views.

Monitor feet even when inactive. Material uncommanded displacement requires withdrawal and reassessment. Measured support holds are candidates, not stability guarantees; never command old anchors beyond limits after slipping. Stop physics on rollout_finished regardless of generic next_call or raw in_progress. After three actions, finish_attempt may end an evidenced stall with a changed hypothesis; this is not success. Do not consume budget with idle holds.

After termination submit a complete revised local skill, concise lesson/change_summary and existing episode public evidence paths within length caps. Shared candidates require cross-task validation and grasp regression; local updates never overwrite the shared core. After explicit no_execution, correct with fresh ID/directory; never replay uncertain execution.

## Task-specific faucet evidence

Objective: move the small water-control lever beyond0.7rad and satisfy native accumulation while stable. Host outcome determines success. No door-style one-second criterion applies. Report visible retention separately.

Episode0001 exhausted74 actions without verified opening/grasp; side approaches, local-X rolls and closure.20–.50 failed. Constrained approaches caused support slip.

Episode0003 stalled after14 actions. Left lifts tracked, but8 had <2mm position error and0.279rad attitude error. Broad plate identity remained unverified; probes10/11 showed no motion. Lower insertion13 caused108/83mm foot displacement; withdrawal14 restored steady feet. Do not repeat it.

Episode0004 ended policy_declared_stall after35 actions/74.16s:24 target_reached,11 timed_out,zero native successes. Feet stayed within0.732/0.464mm of start. Withdrawal33–35 and reopening left no verified retention.

Action1 requested25mm lateral translation of all four points: wrists moved, feet stayed within0.05mm, camera moved mostly forward. No oblique view or locomotion was established;2 canceled foot offsets. Attitude errors9/10 were0.163/0.123rad despite accurate position. High thumb approaches18/19 stalled17/26mm from targets; withdrawal20 tracked. Do not accumulate this unreachable route.

Observation6's thin rear feature at stereo pixels(340.5,182.5)/(322.5,182.5) reconstructed near[-.591,-.062,.831]m, farther/lower than broad surfaces. This episode-local estimate has pixel/depth uncertainty; neither coordinates nor identity transfer.

Partial closure.20 changed the mesh envelope, not grasp state. Thumb-up rolls27–29 tracked46/17/26mrad; actual mesh bounds improved clearance. Lower31 and lateral32 probes established no visible relative control motion;32 moved only2.7mm inward and missed14.3mm. Contact versus tracking constraint remains unresolved. After withdrawal35 the left view exposed the thin stem without clear persistent change; the right remained partly occluded. No opening angle was verified.

Next hypothesis: obtain a genuinely oblique unobstructed view of the rear stem's connection before treating it as the control. Then consider the opposite-side distal-finger route, keeping at least one camera's view of the feature clear. Reuse thumb-up roll only as a tested clearance candidate. Establish a visible response and pivot relationship before continuing rotation. After two tests without verified motion, withdraw and revise.
