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

Push away>=30deg, hold>=1 simulated second, remain standing; never pull handle or close door. Infer panel/frame, hinge side and push area visually. Count native success only. Backend SimpleLiveSim checkpoint PD, corrected frame, not Isaac.

Native successes:0010 right18 chunks/66.84s;0011 left28/105.02s;0012 left31/113.96s;0013 left34/130.86s;0014 left23/92.62s. Final0010-13 timed_out;0014 target_reached. All native_success/rollout_finished=true. Adapt public receipts to reset.

Approach candidate: alternate right/left X200/Z220mm apex then X200 landing,1s each; wrist X totals100,100,100,80,60,40,40mm restoring reset heights~.75m. Support slip reached56mm; yaw drift persists. Short-left150 relocated114-186mm.0010 right150 failed;200 gained153mm.

Raise chosen hand160mm in4x.75s then toward resetZ+.30m in3x1s; alignY visually. Recompute whole-hand bounds, including primitives: wrist height alone is insufficient. Open-hand pushes40-80mmX in2x1s, adaptY to panel arc; preserve a clearance-qualified height.

At reach stall withdraw open hand~180mm and lower over bounded chunks; never pull handle. Recheck wrist relative to passively relocated feet before further withdrawal.0011 lowering alone failed; unloaded left150 gained186mm/support22mm before success. Not robust gait or causal isolation.

0012 unloaded right200 catch-ups21/23 failed:3.7/1.7mmX. Changed left100 gained138mm. Raises passively advanced right68/103mm and missed52mmZ; withdraw40/restore workZ preceded success.

0013 stalls16/26 required recovery. Left100 failed despite38mm rise:14mm peakX,-2mm endpoint; changed150 gained114mm/support10mm before success. Revalidate100.

0014 raise10 passively moved right56X/-52Ymm. Correction12 (+100Z,-20X left; lower right) FAILED: left gained14Z/+43X; inactive feet moved89/149X,-133/-81Ymm,peak164/171mm. Nonterminal stall led to13 withdraw100/lower150,14 recenter140X/lower to reset,15 raise160; feet stabilized.

0014 hand-down extent195mm invalidated old workZ. Active world rotations16/17 Y-.24,Z-.09/-.15rad with raises improved clearance; rotation missed.151/.212rad.19 [0,-.24,-.09] plus20X/30Z achieved handminZ.914 at wrist1.008; saved measured workZ, retaining original1.052.20 X/Y40/-20 opened panel; orientation hold missed.610rad.21-23 X/Y60/-10,80/-10,80/-20 gained54/100/77mm;23 native success. Final feet844/801mmX; no foot commands after8. Passive motion is not gait.

Preserve versions/selections:0001-0007 loaded-foot/rotation/common-translation failures;0008 low fingertip/rotation stalls;0009 low reaches/loaded pushes/late catch-ups.0008/9 voluntary early stops were native in_progress, not terminal physical failures. No proven latch/controller defect. Traces/RGB retained; public video unexposed. Task-local only.
