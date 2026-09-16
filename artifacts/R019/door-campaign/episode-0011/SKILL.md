---
name: loco-manip-direct
description: Apply shared visual control and task-local evidence.
---

## Shared visual control

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Task defines the objective; history supplies candidates. Use only listed public experience, current RGB, calibration, named robot state and robot geometry. No demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference four-point poses, named joints and grippers. Before action, experience_select records source IDs, relevance, adaptations and exclusions; reselect on changed failure mode. Retrieve versions and cited public trajectories selectively. Record problem, goal, observations, decision, uncertainty, forbidden repeats and next hypothesis. Grasp437/438 transfer retrieve-test-observe-correct, not coordinates or door/locomotion success.

Use latest observation path/ID and unique request ID. Reason states evidence, purpose and expected observable change. Await complete responses; physics pauses during reasoning. Inspect fresh RGB and actual poses after every action. Separate reference, tracking, contact hypothesis and progress. No blind replay, unchanged failed retries or cumulative biased reanchoring; preserve reset comparisons.

Supply absolute metre positions and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation. Map joints by name; never output q29 or torques. Grippers ramp 0=open,1=closed. Wrists are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Current observation contract overrides history. Single waypoints use observed limits, currently translation0.03m, rotation0.10rad, duration0.5-3s and retained inactive references. Enabled continuous chunks permit2-5 knots, each0.5-3s,total<=3s. Segment/chunk translation caps: wrists0.06/0.20m, ankles0.30/0.30m; rotation0.10/0.30rad. Start/inactive components equal measured poses; active sets/gripper goals constant. Future samples cross knots; intermediate knots do not await arrival. Reobserve after completion/timeout.

Ray-plane projection is not depth. Use calibrated stereo correspondences; reject shadows, occlusion and ambiguous/inconsistent matches. Check entire-hand clearance, including primitives; recompute after orientation changes. Bounds, closure and target_reached do not prove contact/manipulation. Observe panel relative to frame. Camera lean does not prove walking. Inspect public50Hz pose and commanded/measured joint traces, including transient peaks: endpoint return hides failed motion; ankle rise/tilt does not prove full sole clearance. Pre-PD commands are not measured tracking or a proven controller fault.

Stop actions on rollout_finished. Three actions alone do not justify stopping. At the door, continue useful safe adjustments/pushing/observation; do not end for temporary nonprogress or slow reasoning. finish_attempt may end an evidenced unproductive attempt with a changed hypothesis, never success. Distinguish voluntary stop, budget, safety, infrastructure and native outcome. Then submit complete revised skill, concise lesson/change_summary and existing evidence. Preserve versions, selections and failures within caps. Shared promotion requires cross-task validation and grasp regression.

## SIMPLE asset003 push-open

Push away>=30deg, hold>=1 simulated second, remain standing; never pull the handle or perform close-door. Infer panel/frame, hinge side and push area visually. Count only native success.

0010: first native success, SimpleLiveSim checkpoint PD, corrected frame, not Isaac.18 chunks/3342 steps/66.84s; action18 returned rollout_finished=true/native_success despite wrist tracking timeout. Revalidate after reset. Retrieve0010 executions1-18, RGB and traces before adapting.

Approach1-7 alternated right/left X+200/Z+220mm apex then X+200mm landing,1s each. Wrist X totals100,100,100,80,60,40,40mm, restoring reset heights around0.75m. Support slip reached54mm; yaw drift persisted. Short left8 X150/Z220 relocated119mm. Short right9 X150/Z220 failed:0.10mm endpoint advance,8.62mm peak rise even with low arms. Changed right10 X200/Z220 with wrist40mm follow relocated153mm, support22mm. Reset foot gains656/707mm; stagger51mm. Revalidate clearance and tracking; low arms alone do not guarantee catch-up.

Raise right11 Z160mm in4x0.75s, then12 Z140/Y+40mm in3x1s, retaining X and open fingers, left clear. Position errors4.4/5.7mm; orientation errors0.486/0.500rad. Recompute achieved hand geometry; do not call a new measured quaternion recovery. At12 wristZ1.058m, all hand surfaces above0.938m; indexfrontX-0.249 near visually estimated panelX~-0.2, above handle.

Push13-18 used open right hand above handle, left held clear, feet measured, orientations inactive after failed holds. Keep a fixed working height, not cumulative measured-Z drift. Total right X/Y references by chunk:40/0,40/0,40/-4,60/-10,60/-20,50/-25mm, split into two1s knots. Adapt these candidates to fresh geometry. Actual wrist advances35,37,45,58,66,8mm; final residual44.5mm did not prevent native success/dwell. Stereo and frame gaps showed opening; no angle derived from handle displacement. Feet stayed within submillimetre motion during manipulation.

Preserve failures:0001-0007 small loaded-foot/rotation/common-translation probes;0008 low fingertip pushes/palm rotation;0009 low reaches, large loaded pushes and late raised-arm catch-up stalls.0008/0009 voluntary early stops were native in_progress, not verified terminal physical failures.0010 does not prove why those stalled or establish a latch/controller defect.

Next reset: revalidate closer low-arm stance and high open-hand push, preserve height baselines and observe the door through dwell. Executions/traces/RGB saved; finalized video unexposed. Task-local only.
