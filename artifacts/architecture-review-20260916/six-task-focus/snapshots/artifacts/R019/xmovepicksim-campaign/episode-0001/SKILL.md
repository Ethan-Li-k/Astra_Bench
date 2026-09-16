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

Read this task's latest experience and prior skill selectively. Preserve applicable local lessons, but do not copy cube coordinates or assume task success transfers. Add verified task-specific corrections here after the next physical attempt.
