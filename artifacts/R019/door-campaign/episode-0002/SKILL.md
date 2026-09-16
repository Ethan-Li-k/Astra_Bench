---
name: loco-manip-direct
description: Learn visual G1 SIMPLE manipulation from verified public attempts.
---

# SIMPLE Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. Read the complete task in workspace.json. Push the initially closed SIMPLE asset003 door away from yourself at least 30 degrees relative to its starting position, keep it open at least one simulated second, and remain standing. Use hand contact; never pull the handle or perform the original close-door task. Require ten independent reset successes; other available SIMPLE tasks each require at least one success. Diagnostic replay never counts.

Revise this skill, not weights; no demonstrations. Physics uses registered services only, never another simulator or real robot. Existing environments/runtime stay read-only. Inspect only campaign public evidence, robot geometry, and explicitly listed transferred_self_experience. Never inspect hidden object, hinge, contact, evaluator state or unlisted experiments. Use exactly workspace.json's Python; install nothing. Evidence is read-only; outputs require new descendants of the allowed rollout root.

## Observe, review, execute

Read workspace.json, canonical SKILL.md and experience_read. Selectively retrieve memory/experience.jsonl, memory/versions and cited public rollouts; do not dump archives. Adapt candidates to fresh RGB and named state. Adapt to each reset; never replay blindly.

Call loco_start once with the supplied directory. Inspect available head stereo RGB, calibration, measured/reference poses, named joints and closure. No table plane, object dimensions or calibrated hand TCP are supplied.

Review one bounded waypoint from the latest observation. Use its fresh path/ID, a unique scalebfm_act request ID and an evidence-based reason. Follow returned next_call paths, including geometry calls. Await complete responses. After every action inspect fresh RGB and actual poses; distinguish reference change, tracking, contact hypotheses and task progress. Continue until rollout_finished=true. Change direction, clearance, orientation, step size, duration or closure after failure; never repeat unchanged failures.

## Four-point contract

Map by name in public order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Never copy joint arrays positionally or output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation; inactive components retain references. Measured quaternions alone do not activate tracking. Active targets remain within 0.03 m and 0.10 rad of current measurement; duration 0.5-3 s. Feet normally retain support. Arbitrary foot translations do not establish walking. ScaleBFM/native SIMPLE PD run at 50/200 Hz; physical execution budget is 240 s, paused during reasoning.

Grippers are ramped closure fractions, 0=open and 1=closed. Empty active lists allow gripper-only phases, not contact detection. SIMPLE hand collision geometry differs from prior capsule hands. Infer clearance from current images and robot poses; import no foreign TCP offsets, closure settings or object coordinates.

Geometry tools calculate, never execute: four_point_translate uses world XYZ metres; four_point_rotate uses world axis-angle radians and a pivot; four_point_place_local_point requires an explicitly declared link-local point.

## Perception and verification

Ray-plane projection is not depth. Derive focal length from calibrated image height and vertical FOV. Use reliable stereo correspondences; reject shadows, occlusion intersections and inconsistent edges. Infer door surface, frame and free space from RGB.

Establish actual approach before committing to long arm extension. Verify foot/body advance and clearance rather than counting commanded steps. Establish gentle hand contact, test a small push, and compare door motion with its frame. Continue only consistent progress; relocalize after slip. A moving wrist, closure, overlapping pixels or target_reached does not prove contact/opening. Verify opening, physical dwell and standing separately from native success.

## Tested experience and corrections

Transferred grasp v14 and episodes 437/438 establish the retrieve-test-observe-correct procedure, not door geometry. Original-target holds or isolated rotations sometimes recovered tracking there; none is universal.

R019 episode 0001 ended at the step budget with zero successes. Stereo suggested the door roughly one metre ahead of initial wrists. Unilateral lifts, common forward translations, ankle pitch and differential-height probes did not establish walking; feet barely advanced. Repeated measured-position targets accompanied about 0.60/0.55 m wrist upward drift, without verified contact.

Stop this drift pattern early: do not repeatedly turn biased measurements into new position references. Compare residuals with step bounds and original references. Only activate an original target when still within bounds; otherwise retain inactive references and test a changed bounded candidate. Left local-X rolls of -0.08/-0.09 rad tracked with positions retained in observations 0028-0030 and 0035-0037. Subsequent descent 0038 still failed. These verify attitude tracking only. Support holds also do not establish manipulation progress.

## Audit and learning

Separate construction errors, explicit service errors, tracking timeouts and uncertain transport. Preserve exact errors and layers. Use public receipts and experience_read before retries; never replay uncertain or terminal actions. Explicit terminal wrappers override raw next_call/outcome text.

After success, budget end or fault, read public receipts/trajectory and submit the complete revised skill, concise lesson and exact evidence paths through skill_update. skill_update evidence_paths must name existing files inside this episode's public rollout; agent RPC receipts are not accepted. Check every length cap; caps are ceilings, not targets. Keep learning separate from frozen evaluation. The host continues the campaign.
