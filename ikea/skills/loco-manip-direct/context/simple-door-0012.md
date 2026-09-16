---
name: loco-manip-direct
description: Apply shared visual control and task-local evidence.
---

## Shared visual control

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Use only listed public experience, RGB, calibration, named robot state/geometry. No demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo, calibration, measured/reference four-point poses, named joints and grippers. Before action, experience_select records source IDs, relevance, adaptations and exclusions; reselect on changed failure mode. Retrieve cited public trajectories selectively. Record problem, goal, evidence, uncertainty, exclusions and next hypothesis. Grasp437/438 transfer method, not coordinates or door/locomotion success.

Use latest observation and unique request ID; reason states evidence, purpose and expected change. Await full responses; physics pauses during reasoning. Inspect fresh RGB and actual poses after every action. Separate reference, tracking, contact hypothesis and progress. No blind replay, unchanged failed retries or cumulative biased reanchoring; preserve reset comparisons.

Supply absolute metre positions and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation. Map joints by name; never output q29 or torques. Grippers ramp0=open,1=closed. Wrists are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Current contract overrides history. Use observed single-waypoint limits. Enabled continuous chunks permit2-5 knots, each0.5-3s,total<=3s. Segment/chunk translation caps: wrists0.06/0.20m, ankles0.30/0.30m; rotation0.10/0.30rad. Start/inactive components equal measured poses; active sets/gripper goals constant. Future samples cross knots; intermediate knots do not await arrival. Reobserve after completion/timeout.

Ray-plane projection is not depth. Use calibrated stereo; reject shadows, occlusion and ambiguous/inconsistent matches. Check entire-hand clearance including primitives; recompute after orientation changes. Bounds, closure and target_reached do not prove contact/manipulation. Observe panel relative to frame. Camera lean does not prove walking. Inspect public50Hz pose and commanded/measured joint traces including transient peaks: endpoint return hides failed motion; ankle rise/tilt does not prove sole clearance. Pre-PD commands are not measured tracking or a proven controller fault.

Stop actions on rollout_finished. At the door continue useful safe adjustments/pushing/observation; temporary nonprogress or reasoning delay is not terminal. finish_attempt records an evidenced stall and changed hypothesis, then follow its returned observation/next_call in the SAME episode. Only native termination, safety/system fault or physical budget ends execution. Then submit complete skill_update, lesson/change_summary and existing evidence. Preserve versions, selections and failures within caps. Shared promotion requires cross-task validation and grasp regression.

## SIMPLE asset003 push-open

Push away>=30deg, hold>=1 simulated second, remain standing; never pull handle or close door. Infer panel/frame, hinge side and push area visually. Count only native success. Backend SimpleLiveSim checkpoint PD, corrected frame, not Isaac.

0010 first native success:18 chunks/3342 steps/66.84s, right hand. 0011 second:28 chunks/5251 steps/105.02s, left hand after changed stance. Final actions timed out in tracking but returned native_success/rollout_finished=true. Retrieve executions/RGB/traces from these episodes before adapting.

Approach candidate: alternate right/left X200/Z220mm apex then X200 landing,1s each; wrist X totals100,100,100,80,60,40,40mm restoring reset heights~0.75m. Support slip reached56mm; yaw drift persists. Short-left150/Z220 can relocate119mm. Short-right150 failed in0010; changed200/Z220 with wrists40 relocated153mm. In0011 long-right9 relocated106mm, support45mm. Revalidate actual clearance and support; low arms alone guarantee nothing.

0010 raises: right160mm in4x0.75s, then140/Y+40mm in3x1s. Orientation holds missed~0.5rad; measured quaternion reanchoring is not recovery. Open-hand pushes13-18: X/Y40/0,40/0,40/-4,60/-10,60/-20,50/-25mm in2x1s, fixed height, orientations inactive. Native success despite44.5mm wrist residual.

0011 different reset alignment favored LEFT hand. Raises10/11 transferred160 then140/Y+40mm with inactive orientations; left foot moved22mm during second raise. Pushes12-16 opened panel;17/18 slowed to9.4/4.7mm X, with inward drift. Forward-only60mm still stalled. Withdrawal40/lower50 then80mm lower push ended behind previous maximum; lowering alone did not solve it.

Changed stance succeeded:21 withdraw100/lower100;22 withdraw80/lower to reset height. With both arms low,23 short-left150/Z220 and wrists40mm relocated186mm, right support22mm. Overshoot and peak ankle rise29mm do not prove sole clearance. Raise24 left160/Y+40,25 to original working height/Y+40. Push26-28 X/Y80/+20,80/0,60/-10mm,2x1s, achieved74/79/44mm X;28 native success. Keep a fixed working-height baseline. Final foot gains826/668mm, stagger158mm; right foot moved10.7mm/tilted0.165rad, host verified standing. Recovery is not causal isolation or robust gait.

Preserve0001-0007 loaded-foot/rotation/common-translation failures;0008 low fingertip/palm-rotation stalls;0009 low reaches, loaded pushes and late raised-arm catch-up stalls. 0008/0009 were voluntary early stops with native in_progress, not terminal physical failures. 0011 finish_attempt continued. No proven latch/controller defect.

Next reset: select hand visually, establish close low-arm stance, raise above handle and follow panel. If reach stalls, unload before changing stance; never blindly mirror paths. Executions/traces/RGB retained; finalized video unexposed. Task-local only.
