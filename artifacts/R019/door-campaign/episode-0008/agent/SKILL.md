---
name: loco-manip-direct
description: Apply shared visual control methods and task-local evidence.
---

## Shared methods from grasp v14

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Task defines the objective; history supplies candidates. Use only listed public experience, current RGB, calibration, named robot state and geometry. No demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference four-point poses, named joints and gripper closure. Before action, experience_select identifies source IDs, relevance, adaptations and exclusions; reselect when failure mode changes. Retrieve relevant versions and cited public trajectories selectively. Record observations, goal, decision, uncertainty, forbidden repeats and next hypothesis in public evidence.

Grasp437/438 support retrieve-test-observe-correct. Their coordinates, geometry, closure and orientation need fresh validation. Ten native grasp successes, five endpoint-retained, do not establish locomotion or door success.

Use latest observation path/ID and unique request ID. Reason states evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. After each action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Change a justified variable after failure; no blind replay, unchanged retries or cumulative biased reanchoring.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation. Map joints by name; never output q29 or torques. Grippers are ramped closure fractions: zero open, one closed. Wrists are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Current observation contract overrides older limits. Single waypoints use observed per-link translation bounds (currently 0.03m), 0.10rad rotation, 0.5-3s duration and retained inactive references. Explicitly enabled continuous chunks allow 2-5 knots, each 0.5-3s, total <=3s. Segment/chunk translation caps: wrists 0.06/0.20m; ankles 0.30/0.30m. Rotation caps: 0.10rad/segment, 0.30rad/chunk. Start/inactive components equal current measured poses; active sets and gripper goals stay constant. Future samples cross knots; intermediate references do not await arrival. Reobserve after completion/timeout. Preserve reset comparisons despite measured anchors.

Ray-plane projection is not depth. Use calibrated conventions and reliable stereo correspondence; reject shadows, occlusion and inconsistent reprojections. Check entire-hand clearance and reobserve after contact. Closure, wrist displacement, target_reached and pixel overlap cannot prove manipulation. Probe relationships physically and observe independently. Camera lean or arm tracking cannot prove walking. Inspect public 50Hz named pose traces and peak ankle samples: endpoint return cannot establish transient motion; ankle rise alone cannot establish full foot clearance/support.

Stop actions on rollout_finished. After at least three actions, finish_attempt may end an evidenced stall with a changed hypothesis; never count it as success or stop merely for slow reasoning. Avoid idle budget consumption. Then submit complete revised skill, concise lesson/change_summary, transfer_scope and existing episode evidence. Preserve versions, selections and feedback within caps. Task-local updates do not overwrite shared core; shared promotion requires cross-task validation and a grasp regression check.

## SIMPLE asset003 push-open

Push the initially closed door away >=30 degrees, hold >=1 simulated second and remain standing. Do not pull its handle or follow the original close-door task. Visually locate panel, frame, hinge side and push area; approach before reaching. Count only native success verifying contact, opening, dwell and standing.

R019/0001: measured-wrist reanchoring caused Z drift; no approach. 0002: small lift-forward, common X translation and toe-up failed. 0003: ankle roll/yaw failed; feet <0.11mm. Do not repeat unchanged.
0004: paired wrist Y+20/+40mm tracked, +60 failed; camera Y+28.745mm, feet <0.378mm. Right Z+15mm failed with/without active wrists.
0005: symmetric original-orientation coordination failed. Frozen achieved-orientation baseline briefly tracked, lateral40 failed; feet <0.170mm. Changed-reference tracking was not original-pose recovery.
0006, checkpoint PD, SimpleLiveSim: three continuous chunks, 8.42s, stall/no success. Right wrist Y+80mm moved77.27mm; sustained right ankle +40/+80mm rose only0.04648mm despite wrist errors2.20/3.82mm. Feet snapshots <0.118mm. Do not repeat lateral escalation or sustained clearance unchanged.

0007, same backend/profile: three 1s chunks, 177 steps/3.54s, explicit rollout_finished/stall, no success. Right/left ankle +40mm lift-return (0.5s up/down) peaked only0.022387/0.009965mm. Matching right-wrist pulse peaked28.926mm. All final targets reached; none proved foot clearance. Public traces contain67/62/51 samples; maximum reset-relative ankle displacement0.099168mm. Final stereo/support consistent with standing; door still beyond reach, contact/opening/dwell unverified. Wrist position recovery was not original-orientation recovery. Sequential posture differed, so comparison does not isolate a control fault.

Next unverified hypothesis: public synchronized named leg-joint reference/actual traces can distinguish absent leg-reference response from failed downstream tracking/support response. Compare against the wrist pulse control. Do not inspect runtime or hidden state. Obtain this public diagnostic before more unchanged lift-return, sustained lifts or forward swings; no proven defect or walking skill yet.
