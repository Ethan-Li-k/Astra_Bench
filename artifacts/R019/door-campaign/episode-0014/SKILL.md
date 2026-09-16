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

Native successes:0010 right18 chunks/66.84s;0011 left28/105.02s;0012 left31/113.96s;0013 left34/130.86s. Final actions timed_out in tracking but native_success/rollout_finished=true. Retrieve cited evidence; adapt to reset.

Approach candidate: alternate right/left X200/Z220mm apex then X200 landing,1s each; wrist X totals100,100,100,80,60,40,40mm restoring reset heights~.75m. Support slip reached56mm; yaw drift persists. Short-left150/Z220 relocated114-186mm.0010 short-right150 failed; changed200 gained153mm.

Raise chosen hand160mm in4x.75s then to fixed workZ~resetZ+.30m in3x1s; alignY visually. Check whole hand above handle. 0010 orientation holds missed~.5rad; inactive orientations drift. Open-hand pushes40-80mmX in2x1s, adaptY to panel arc, preserve workZ.

At reach stall withdraw open hand~180mm and lower to reset over bounded chunks; no handle pull.0011 lower-only push stayed behind old maximum; short-left150 after withdrawal gained186mm/support22mm, then raised pushes succeeded. Recovery is not causal isolation or robust gait.

0012 high push18 gained9.3mm for60mm. Withdrawal/lowering did not rescue right200/Z220 catch-ups21/23:3.7/1.7mmX and4.3/2.4mm rise. Changed left100/Z220 with wrists30 gained138mm; feet288mm stagger. Raises passively advanced right68/103mm, missed52mm height. Withdraw40/restore original workZ before pushes28-31 succeeded.

0013 approach1-9 gained637/645mm at feet;7/9 left support retreated50/45mm. Handle~Z.866; workZ1.0523 cleared hand.14 visibly opened panel.16/26 saturated13/9mmX for60mm; both nonterminal finish_attempt calls led to recovery. Withdrawal/lowering17/18 then left150/Z220,wrists40 in19 gained156mm/support16mm. Push24 passively advanced right63mm (70mm peak excursion); not commanded gait.

Second unload27/28 then left100/Z220,wrists30 in29 FAILED:37.8mm rise,14.4mm peakX,-2.1mm endpointX. Changed150mmX with same Z/timing/wrists in30 gained114mm/support9.7mm. Amplitude causality not isolated. Raises31/32 restored workZ with foot peaks<.5mm. Pushes33/34 X/Y80/0,80/-10 gained83/73mm;34 native success. Final foot gains909/700mm,stagger210mm. Revalidate short100.

Preserve0001-0007 loaded-foot/rotation/common-translation failures;0008 low fingertip/palm-rotation stalls;0009 low reaches/loaded pushes/late raised-arm catch-up stalls.0008/0009 were voluntary early stops with native in_progress, not terminal physical failures. No proven latch/controller defect. Versions, selections, traces/RGB retained; video unexposed. Task-local only.
