---
name: loco-manip-direct
description: Apply shared visual control methods and task-local evidence.
---

## Shared visual control

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Task defines the objective; history supplies candidates. Use only listed public experience, current RGB, calibration, named robot state and geometry. No demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference four-point poses, named joints and grippers. Before action, experience_select records source IDs, relevance, adaptations and exclusions; reselect on changed failure mode. Retrieve versions and cited public trajectories selectively. Record problem, goal, observation, decision, uncertainty, forbidden repeats and next hypothesis in public evidence.

Grasp437/438 support retrieve-test-observe-correct, not transferred coordinates, locomotion or door success.

Use latest observation path/ID and unique request ID. Reason states evidence, purpose and expected observable change. Await complete responses; physics pauses during reasoning. Inspect fresh RGB and actual poses after every action. Separate reference, tracking, contact hypothesis and task progress. No blind replay, unchanged failed retries or cumulative biased reanchoring; preserve reset comparisons.

Supply absolute metre positions and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation. Map joints by name; never output q29 or torques. Grippers are ramped fractions:0 open,1 closed. Wrists are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Current observation contract overrides history. Single waypoints use observed translation limits (currently0.03m), rotation0.10rad, duration0.5-3s and retained inactive references. Enabled continuous chunks permit2-5 knots, each0.5-3s,total<=3s. Segment/chunk translation caps: wrists0.06/0.20m, ankles0.30/0.30m; rotation0.10/0.30rad. Start/inactive components equal measured poses; active sets/gripper goals constant. Future samples cross knots; intermediate knots do not await arrival. Reobserve after completion/timeout.

Ray-plane projection is not depth. Use calibrated stereo correspondences; reject shadows, occlusion and inconsistent/ambiguous matches. Check entire-hand clearance and recompute geometry after orientation changes. Mesh bounds, closure, overlap and target_reached cannot prove contact/manipulation. Observe panel relative to frame. Camera lean cannot prove walking. Inspect public50Hz pose and commanded/measured joint traces, including transient peaks: endpoint return hides failed motion; ankle rise/tilt does not establish full sole clearance. Commands before PD are not measured tracking or a proven controller fault.

Stop actions on rollout_finished. After>=3 actions, finish_attempt may end an evidenced stall with a changed hypothesis, never success or merely slow reasoning. Avoid idle budget use. Then submit complete revised skill, concise lesson/change_summary, existing evidence and transfer_scope. Preserve versions, selections and failures within caps. Shared promotion requires cross-task validation and grasp regression.

## SIMPLE asset003 push-open

Push away>=30deg, hold>=1 simulated second, remain standing. Do not pull the handle or follow the original close-door task. Locate panel/frame/hinge side/push area visually; approach before reaching. Count only native contact/opening/dwell/standing success.

R019/0001-0007: wrist reanchoring caused Z drift; small lifts, common translation, toe-up, ankle rotations and lateral wrist escalation failed. Achieved-reference tracking was not original-pose recovery. 0006 sustained40/80mm lifts failed. 0007 ankle40mm return peaks0.022/0.010mm versus28.926mm wrist; endpoints reached. Do not replay unchanged.

0008, SimpleLiveSim checkpoint PD, not Isaac:17 chunks,3304 steps/66.08s,15 timeouts/2 reached. Host finish_attempt confirmed rollout_finished/stall; native in_progress,0 successes. Leg commands and knees responded, rejecting universal immobile-feet hypotheses, not proving a control defect.

Approach candidate: action1 coordinated150mm landing failed; action2 right X+200/Z+100mm return rose4.525mm. After arm recovery, action4 X+200/Z+220mm over1s then return over1s rose52.735mm and retained127.342mm forward despite timeout. Actions5-10 adapted alternating high-clearance references, forward landing and wrist coordination. Retrieve these public executions/traces before reuse. Later two-knot candidates used swing X+200/Z+220mm then X+200mm landing,1s each; wrists X+50/+100mm or smaller. Final ankle reset gains were585/547mm; support slip reached42mm and yaw drift remained. Right yaw correction failed. This is one task-local approach candidate, not a validated gait or full-clearance proof; revalidate after reset and stop swings near panel.

Manipulation stalled. Stereo handle/vent stayed nearX-0.22/-0.20m here; not reusable coordinates. Raised-left30/40mm and lower-right40/120mm forward probes left panel visibly closed. Both index mesh bounds stopped nearX-0.25m: contact/resistance plausible, unverified. Right120mm push retained106.82mm wrist error. Withdrawal80mm tracked2.74mm, but0.18rad palm rotation missed0.42068rad; fixed palm-goal error worsened1.007->1.131rad. Final stereo/support consistent with standing; opening/dwell unverified. Do not repeat fingertip escalation or palm rotation unchanged.

Next unverified hypothesis: withdraw, clear the other hand, move tangentially toward the visible free-edge panel below the handle, then test a bounded lower push for greater leverage. Recompute clearance; require panel/frame motion and native success. Do not infer a latch, contact truth or mechanism defect. Public files exposed no finalized video; recording finalization remains unverified.
