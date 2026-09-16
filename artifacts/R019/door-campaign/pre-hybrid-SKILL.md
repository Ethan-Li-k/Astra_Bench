---
name: loco-manip-direct
description: Learn visual G1 SIMPLE manipulation from verified public attempts.
---

# SIMPLE Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json's complete task. Push the initially closed SIMPLE asset003 door away at least 30 degrees, hold it open at least one simulated second, and remain standing. Use hand contact; never pull the handle or perform the original close-door task. Require ten independent reset successes; other SIMPLE tasks require one. Diagnostic replay never counts.

Revise this skill, not weights; no demonstrations. Execute physics only through registered services, never another simulator or real robot. Existing environments/runtime remain read-only. Inspect only campaign public evidence, robot geometry and explicitly listed transferred_self_experience. Never inspect hidden object, hinge, contact, evaluator state or unlisted experiments. Use workspace.json's exact Python; install nothing. Evidence is read-only; new outputs belong under the allowed rollout root.

## Observe, review, execute

Read canonical SKILL.md and experience_read. Retrieve memory versions and cited public rollouts selectively. Adapt candidates to fresh RGB and named state; never replay blindly. Revalidate controller response each episode.

Call loco_start once with the supplied directory. Inspect head stereo RGB, calibration, measured/reference poses, named joints and closure. No table plane, object dimensions or calibrated hand TCP are supplied.

Review one bounded waypoint from the latest observation. Use its fresh path/ID, a unique scalebfm_act request ID and an evidence-based reason. Follow returned next_call paths, including geometry calls. Await complete responses. After every action inspect fresh RGB and actual poses. Separate reference changes, tracking, contact hypotheses and task progress. Change direction, clearance, orientation, step size, duration or closure after failure; never repeat unchanged failures.

Continue until rollout_finished=true. After at least three executed actions, end an evidenced stall with finish_attempt and a changed hypothesis instead of repeated idle holds. This is failure, not success. Submit skill_update after confirmed termination; the host continues the campaign.

## Four-point contract

Map by name in public order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Never copy joint arrays positionally or output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation. Inactive components retain references, even when geometry tools return measured poses. Measured quaternions do not activate tracking. Active targets stay within 0.03 m and 0.10 rad of measurement; duration 0.5-3 s. Feet normally retain support. ScaleBFM/native SIMPLE PD run at 50/200 Hz; physical budget is 240 s, paused during reasoning.

Grippers are ramped closure fractions: 0=open, 1=closed. Empty active lists permit gripper-only phases, not contact detection. SIMPLE hand collisions differ from capsule hands. Infer clearance from current images/poses; import no foreign TCP offsets, closure settings or object coordinates.

Geometry tools calculate without execution: translate uses world XYZ metres; rotate uses world axis-angle radians and a pivot; place_local_point requires an explicitly declared link-local point.

## Perception and verification

Ray-plane projection is not depth. Derive focal length from calibrated height and vertical FOV. Use reliable stereo correspondences; reject shadows, occlusion intersections and inconsistent edges. Infer door, frame and free space from RGB.

Establish actual approach before long arm extension. Verify ankle advance and body clearance; wrist motion or camera lean alone is not walking. Establish gentle hand contact, test a small push and compare door motion with its frame. Relocalize after slip. Closure, overlapping pixels or target_reached do not prove contact/opening. Verify opening, physical dwell and standing separately from native success.

## Tested experience

Transferred grasp v14/437/438 informs procedure, not door geometry.

R019/0001 exhausted its budget without approach. Reanchoring measured wrists accompanied 0.60/0.55 m upward drift. Compare residuals with original references; activate original targets only within bounds. Left local-X rolls tracked, but descent failed.

R019/0002 checkpoint body PD: lift-forward, common +20 mm X and toe-up lift timed out without ankle advance. Brief wrist tracking was not walking. Original support recovery tracked; ended as policy_declared_stall.

R019/0003 checkpoint body PD: isolated right ankle +0.08 rad world-X roll and bilateral +0.06 rad world-Z yaw timed out with 0.0806/0.0603 rad residuals. Observed ankle shifts stayed under 0.11 mm; no approach or unloading established. Restoring original ankles tracked (1.12 mm/0.00663 rad). Three actions, 7.28 s, policy_declared_stall; contact/opening/dwell unverified. Do not repeat these orientation probes unchanged.

Next hypothesis, unverified: bounded paired-wrist lateral shift while correcting existing X/Z reference error, retaining original ankles. Require camera-midpoint and named hip/waist response before considering swing; wrist-only tracking does not establish load transfer or clearance.

## Audit and learning

Separate construction errors, service errors, tracking timeouts and uncertain transport. Preserve exact errors/layers. Consult public receipts and experience_read before retries; never replay uncertain or terminal actions. Explicit terminal wrappers override raw next_call/native outcome.

After termination, audit public receipts/trajectory and submit a complete revised skill, concise lesson and exact existing evidence files through skill_update. Evidence must be inside this episode's public rollout; agent RPC receipts are invalid. Check all length caps and retain versioned evidence. Keep learning separate from frozen evaluation.
