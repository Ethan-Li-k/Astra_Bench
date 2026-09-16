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

Push away>=30deg, hold>=1 simulated second, remain standing; never pull the handle or perform close-door. Infer panel/frame, hinge side and push area visually. Count only native success.

0001-0007 small loaded-foot lifts, common translations, toe-up, ankle rotations and lateral wrist escalation failed; endpoint arrival hid absent swing. 0008 high-clearance references produced approach, with slip/yaw drift; low fingertip pushes and palm rotation stalled. Revalidate contact under0009's corrected frame collision.

0009, SimpleLiveSim checkpoint PD, not Isaac:40 chunks,7834 steps/156.68s;33 timeouts/7 reached. finish_attempt confirmed rollout_finished/policy_declared_stall; native in_progress,0 successes. Partial opening is not verified30deg/contact/dwell/standing success.

Approach candidate: retrieve0008 actions4-10 and0009 actions1-7 before reuse. Alternating X+200/Z+220mm apex then X+200mm landing,1s each, with bounded wrist advance, relocated feet after reset. Reduce arm advance near panel and preserve height baselines. After0009 action7 ankle X gains551.55/543.50mm; support displacement reached64.64mm. Not a validated gait or sole-clearance proof. Short left action22 X150/Z220mm relocated210.39mm; right23 advanced0.806mm. Revised right40 X200/Z220,1.5/1.5s, wrists X40/80mm advanced6.479mm while left support retreated157.532mm. Do not retry these late raised-arm swings unchanged. Final reset gains605.60/552.88mm do not erase lost support.

Manipulation: low open/folded right reaches tracked poorly, including downward motion after withdrawal; resistance alone is unsupported. Fixed orientation briefly tracked, then missed0.404rad during raising. Raised closed right push18 produced panel/frame separation; high free-edge and bilateral pushes later stalled. Opening fingers34 renewed motion. Calibrated stereo suggests~164mm handle X change17->37, not an angle estimate. Action37 X120/Y-30mm references yielded32.7mm handle advance;38 X160/Y-42mm left155/159mm wrist residuals. No further loaded amplitude escalation unchanged. Retrieve executions/RGB and recompute full-hand geometry; these are partial-opening candidates, not door success.

Next unverified hypothesis: establish closer balanced support with lower arms before raising for contact; validate right catch-up first. Compare unloaded forward reach beside the panel with matched high contact motion, retaining fixed height/orientation goals and public joint traces. No proven latch/controller fault. Public RGB/traces/receipts exist; finalized video remains unexposed.
