---
name: loco-manip-direct
description: Apply shared visual control methods and task-local evidence.
---

## Shared methods from grasp v14

Use gpt-6-astra/xhigh. Read workspace.json, its detailed task_specification, the assembled SKILL.md and experience_read. The task specification defines the objective; skill history supplies candidates, never a replacement objective. No human demonstrations, hidden object/contact state, evaluator inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing. Only listed public sources and robot geometry are available.

Call loco_start once. Inspect current RGB, camera calibration, named measured/reference robot poses, joints and gripper closure. Before acting, call experience_select: identify selected source IDs, why they apply, what needs adaptation and what you will not reuse. Re-select when the failure mode changes. Retrieve only relevant versions and cited public trajectories. Preserve concise progress, uncertainties and next hypotheses in notes.

Grasp episodes437/438 succeeded after retrieving earlier self-generated success and validating it against current observations. Transfer that retrieve-test-observe-correct procedure. Their coordinates, capsule geometry, table plane, closure fractions and grasp orientation require fresh validation on other tasks. Ten native grasp successes included five endpoint-retained successes; neither implies locomotion or task transfer success.

Use one reviewed waypoint, the latest observation path/ID and a unique request ID. In reason, state observed evidence, action purpose and expected observable change. After the blocking action, inspect fresh RGB and actual poses. Separate target request, tracking, contact hypothesis and task progress. Change a justified variable after failure; avoid unchanged retries and accumulating biased measurement anchors.

Four named points: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all absolute world positions in metres and unit wxyz quaternions. Declare active.position/orientation; inactive components retain references. Respect reported translation limits, 0.10 rad rotation and 0.5-3 s duration. Never output q29 or torques. Grippers.left/right are ramped closure fractions: zero open, one closed. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Ray-plane projection is not depth. Use calibrated camera conventions and reliable stereo correspondence; reject shadows, occlusion and inconsistent reprojections. Check clearance for the entire hand. Reobserve after contact. Commanded closure, wrist displacement, target_reached or overlapping pixels cannot prove object manipulation. Use a short physical probe followed by independent observation/hold to test the task-relevant relationship. Preserve uncertainty when views disagree.

Await complete model and service responses; reasoning delay is not action failure. Simulation currently pauses during reasoning. Stop physical actions on rollout_finished. After at least three completed actions, finish_attempt can document an evidenced stall and changed hypothesis; it is never success. Do not fill the remaining budget with idle holds.

After termination, submit a complete revised local skill, concise change_summary, lesson, transfer_scope and existing public evidence paths. Mark task-specific rules separately from shared_candidate ideas. Local revisions never overwrite the shared core. Promote a shared candidate only after cross-task validation and a grasp regression check. Preserve decisions, tool feedback, revisions and source selection; do not export private chain-of-thought. Keep the assembled skill within all length caps.

## Task specialization

Transferred grasp v14/437/438 informs procedure, not door geometry.

R019/0001 exhausted its budget without approach. Reanchoring measured wrists accompanied 0.60/0.55 m upward drift. Compare residuals with original references; activate original targets only within bounds. Left local-X rolls tracked, but descent failed.

R019/0002 checkpoint body PD: lift-forward, common +20 mm X and toe-up lift timed out without ankle advance. Brief wrist tracking was not walking. Original support recovery tracked; ended as policy_declared_stall.

R019/0003 checkpoint body PD: isolated right ankle +0.08 rad world-X roll and bilateral +0.06 rad world-Z yaw timed out with 0.0806/0.0603 rad residuals. Observed ankle shifts stayed under 0.11 mm; no approach or unloading established. Restoring original ankles tracked (1.12 mm/0.00663 rad). Three actions, 7.28 s, policy_declared_stall; contact/opening/dwell unverified. Do not repeat these orientation probes unchanged.

Next hypothesis, unverified: bounded paired-wrist lateral shift while correcting existing X/Z reference error, retaining original ankles. Require camera-midpoint and named hip/waist response before considering swing; wrist-only tracking does not establish load transfer or clearance.
