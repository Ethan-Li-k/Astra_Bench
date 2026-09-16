---
name: loco-manip-direct
description: Apply shared visual control methods and task-local evidence.
---

## Shared methods from grasp v14

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. The task defines the objective; history supplies candidates. Use only listed public experience, current RGB, calibration, named robot state and robot geometry. No human demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference four-point poses, named joints and gripper closure. Before physical action, experience_select must identify source IDs, relevance, adaptations and exclusions. Re-select when the failure mode changes. Retrieve relevant versions and cited public trajectories selectively. Record concise observations, decisions, uncertainties and next hypotheses in public evidence.

Grasp437/438 support retrieve-test-observe-correct using earlier self-generated success. Their coordinates, capsule/table geometry, closure fractions and grasp orientation need fresh validation. Ten native grasp successes, including five endpoint-retained successes, do not establish locomotion or door success.

Use one reviewed waypoint with latest observation path/ID and unique request ID. Reason must state observed evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. After each action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Change a justified variable after failure; no blind replay, unchanged retries or cumulative biased reanchoring.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect current per-link limits (currently 0.03 m), 0.10 rad rotation and 0.5-3 s duration. Compare active targets to fresh measurements; original references can exceed bounds. Never output q29 or torques. Map joint quantities by name, never presumed order. Grippers are ramped closure fractions, zero open/one closed. Wrist frames are not calibrated TCPs. Geometry tools only calculate; scalebfm_act executes.

Ray-plane projection is not depth. Use calibrated camera conventions and reliable stereo correspondence; reject shadows, occlusion and inconsistent reprojections. Check entire-hand clearance and reobserve after contact. Closure commands, wrist displacement, target_reached and overlapping pixels cannot prove manipulation. Use a short physical probe plus independent observation/hold to test the relevant relationship. Preserve uncertainty when views disagree. Camera lean or arm tracking cannot prove walking; require actual foot clearance/advance and support evidence.

Stop physical actions on rollout_finished. After at least three actions, finish_attempt may terminate an evidenced stall with a changed hypothesis; it is never success. Do not spend the budget on idle holds. After termination submit the complete revised skill, concise lesson/change_summary, transfer_scope and existing current-episode evidence files. Keep all length caps; preserve versions, selections and feedback without private reasoning. Task-specific revisions never overwrite shared core. Promote shared_candidate ideas only after cross-task validation and a grasp regression check.

## Task-specific: SIMPLE asset003 push-open

Push the initially closed door away at least 30 degrees, hold at least one simulated second and remain standing. Do not pull its handle or follow the original close-door task. Locate panel, frame, hinge side and accessible push area visually. Approach before reaching if needed. Count only native success; host verifies contact, opening, dwell and standing.

R019/0001: no approach; measured-wrist reanchoring accompanied +0.60/+0.55 m Z drift. Local-X rolls tracked but descent failed. Compare original references.
0002 checkpoint body PD: lift-forward, common +20 mm X and toe-up failed without ankle advance.
0003: right ankle +0.08 rad world-X roll and bilateral +0.06 rad world-Z yaw failed; ankle displacement <0.11 mm. Do not repeat these probes unchanged.

0004: position-only paired wrist Y+20/+40 mm tracked; +60 mm failed. Camera Y reached +28.745 mm, but ankle snapshots moved <0.378 mm. Right original-Z+15 mm failed both alone and with wrists active. Better wrist tracking did not establish unloading.

0005 checkpoint body PD: five actions, 13.08 s, policy_declared_stall, no success. Wrist X/Z correction with original orientations and lateral20 both timed out on left orientation (0.103/0.124 rad), despite position errors <=3.18 mm. A once-captured achieved orientation at fixed positions tracked (0.048/0.027 rad); lateral40 with those frozen quaternions failed (0.078/0.030 rad). Camera Y then was only +0.491 mm; ankle snapshot displacement stayed <0.170 mm. Rollback tracked positions, yet final left orientation was 0.236 rad from the reset reference. Changed-reference residual improvement is not original-pose recovery. Do not repeatedly reanchor or escalate this symmetric sequence. Final stereo/support were consistent with standing; contact/opening/dwell remained unverified.

Next hypothesis, unverified: asymmetric right-only lateral wrist coordination with left arm and original ankles retained. Right orientation tracked better than left during symmetric trials. From fresh reset establish a bounded fixed baseline, vary only right wrist Y, and require reproducible camera/hip response plus actual support/clearance evidence before swing. Do not replay symmetric shifts or loaded-foot lifts unchanged.
