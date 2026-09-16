---
name: loco-manip-direct
description: Apply shared visual control methods and task-local evidence.
---

## Shared methods from grasp v14

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Task defines the objective; history supplies candidates. Use only listed public experience, current RGB, calibration, named robot state and robot geometry. No human demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference four-point poses, named joints and gripper closure. Before action, experience_select must identify source IDs, relevance, adaptations and exclusions. Re-select when failure mode changes. Retrieve relevant versions and cited public trajectories selectively. Record observations, goal, decision, uncertainty, forbidden repeats and next hypothesis in public evidence.

Grasp437/438 support retrieve-test-observe-correct using self-generated success. Their coordinates, geometry, closure and orientation need fresh validation. Ten native grasp successes, including five endpoint-retained successes, do not establish locomotion or door success.

Use the latest observation path/ID and unique request ID. Reason states observed evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. After each action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Change a justified variable after failure; no blind replay, unchanged retries or cumulative biased reanchoring.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation. Map joints by name; never output q29 or torques. Grippers are ramped closure fractions: zero open, one closed. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Current observation contract overrides older limits. Single waypoints use observed per-link translation bounds (currently 0.03 m), 0.10 rad rotation, 0.5-3 s duration and retained inactive references. Only when explicitly enabled, continuous chunks allow 2-5 knots, each 0.5-3 s, total <=3 s. Current segment/chunk translation caps: wrists 0.06/0.20 m; ankles 0.30/0.30 m. Rotation caps are 0.10 rad/segment and 0.30 rad/chunk. Start and inactive components equal current measured poses; active sets and gripper goals stay constant. Future samples cross knots; intermediate references do not await arrival. Reobserve after completion or timeout. Preserve reset comparisons despite required measured anchors.

Ray-plane projection is not depth. Use calibrated conventions and reliable stereo correspondence; reject shadows, occlusion and inconsistent reprojections. Check entire-hand clearance and reobserve after contact. Closure, wrist displacement, target_reached and overlapping pixels cannot prove manipulation. Test relationships with a short physical probe and independent observation. Camera lean or arm tracking cannot prove walking; require actual foot clearance/advance and support evidence. Endpoint return cannot prove transient movement.

Stop actions on rollout_finished. After at least three actions, finish_attempt may terminate an evidenced stall with a changed hypothesis; never count it as success. Avoid idle budget consumption. Then submit complete revised skill, concise lesson/change_summary, transfer_scope and existing episode evidence. Preserve versions, selections and feedback within all caps. Task-local updates do not overwrite shared core. Promote shared_candidate only after cross-task validation and a grasp regression check.

## SIMPLE asset003 push-open

Push the initially closed door away >=30 degrees, hold >=1 simulated second and remain standing. Do not pull its handle or follow the original close-door task. Visually locate panel, frame, hinge side and push area; approach before reaching. Count only native success verifying contact, opening, dwell and standing.

R019/0001: measured-wrist reanchoring caused large Z drift; no approach. 0002: small lift-forward, common X translation and toe-up failed. 0003: ankle roll/yaw failed; feet moved <0.11 mm. Do not repeat unchanged.

0004: paired wrist Y+20/+40 mm tracked; +60 failed. Camera Y reached +28.745 mm, feet <0.378 mm. Right Z+15 mm failed with and without active wrists.
0005: symmetric original-orientation coordination failed. A frozen achieved-orientation baseline briefly tracked but lateral40 failed; feet <0.170 mm. Changed-reference tracking was not original-pose recovery.

0006, checkpoint PD, SimpleLiveSim: three continuous chunks, 8.42 s, policy_declared_stall, no success. Right-only wrist Y+40/+80 mm moved 77.27 mm but timed out at 0.06067 rad; camera Y only +4.113 mm. Right ankle Z+40/+80 mm over two 0.5-s segments failed: actual rise 0.04648 mm, residual 79.954 mm despite wrist errors 2.20/3.82 mm. Recovery tracked positions; final stereo/support consistent with standing. Across snapshots feet moved <0.118 mm. No contact/opening/dwell verified. Do not repeat asymmetric lateral escalation or sustained clearance unchanged.

Next unverified hypothesis: compare an in-place lift-return arc, with fixed wrists and a future landing reference, against sustained clearance. Require public within-chunk named ankle samples or foot-visible RGB to establish transient clearance/support before forward swing. Endpoint observations alone neither prove motion nor identify a control-chain fault.
