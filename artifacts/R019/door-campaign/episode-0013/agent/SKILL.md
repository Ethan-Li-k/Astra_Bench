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

Native successes:0010 right hand18 chunks/66.84s;0011 left28/105.02s;0012 left31/113.96s. Final actions timed_out in tracking but native_success/rollout_finished=true. Retrieve cited executions/RGB/traces; adapt to reset alignment/depth.

Approach candidate: alternate right/left X200/Z220mm apex then X200 landing,1s each; wrist X totals100,100,100,80,60,40,40mm restoring reset heights~.75m. Support slip reached56mm; yaw drift persists. Short-left150/Z220 relocated119-186mm.0010 short-right150 failed; changed200/Z220 gained153mm. Low arms alone guarantee nothing.

Raise chosen hand160mm in4x.75s then to fixed working height~resetZ+.30m in3x1s, adjustY visually. Check entire hand above handle; orientation holds missed~.5rad in0010. Inactive orientations permit drift, not recovery. Open-hand pushes40-80mmX in2x1s, adaptY to observed panel arc and keep saved workZ.0010 final residual44.5mm.

0011 high left pushes stalled; lower-only push stayed behind old maximum. Withdrawing180mm/lowering to reset, then short-left150/Z220 with wrists40 gained186mm; support22mm. Re-raise and pushes80/+20,80/0,60/-10mm X/Y succeeded. Recovery is not causal isolation or robust gait.

0012 approach1-7 gained581/585mm at feet;7 left support retreated38mm. Short-left8 X150/Z220 gained175mm/support8mm, then high left pushes opened panel.18 stalled9.3mmX for60mm request/residual53mm. finish_attempt was nonterminal and19 continued. Withdrawal/lowering19/20 unloaded; right200/Z220 catch-up21 failed3.7mmX/4.3mm peakZ. Further left retraction112mm22 did not rescue23:1.7mmX/2.4mm rise, knees active. Change failed references.

Changed short-left24 X100/Z220 with wrists30 gained138mm (38mm overshoot), right support17mm; feet stagger288mm. Raises25/26 caused passive right advances68/103mm, peak excursions74/106mm; NOT stable support or a commanded gait.26 missed52mm height.27 withdrew40/restored height; feet settled.28-31 reapproach/push X/Y60/0,80/-40,80/0,60/-10mm at originalZ1.05753 gained59/88/107/56mmX;31 native success. Foot gains882/779mm, stagger103mm. Correct inadequate whole-hand height before pushing.

Preserve0001-0007 loaded-foot/rotation/common-translation failures;0008 low fingertip/palm-rotation stalls;0009 low reaches/loaded pushes/late raised-arm catch-up stalls.0008/0009 were voluntary early stops with native in_progress, not terminal physical failures. No proven latch/controller defect. At reach stall unload and change hypothesis; no blind mirroring. Executions/traces/RGB retained; video unexposed. Task-local only.
