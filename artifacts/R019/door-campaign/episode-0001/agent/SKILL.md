---
name: loco-manip-direct
description: Transfer learned visual G1 control to SIMPLE manipulation and revise from actual attempts.
---

# SIMPLE Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. Read the complete current task in workspace.json. First push the initially closed door open at least 30 degrees relative to its starting position, keep it open at least one simulated second, and remain standing. Use hand contact to push, not pull. Ten independent successes are required. This uses SIMPLE asset003, configured as a push-open variant. Other available SIMPLE manipulation tasks each require at least one success. Diagnostic replay never counts as a policy trial.

Revise this skill, not weights; no demonstrations. Use registered services for physics; no second simulator or real robot. Existing environments/runtime remain read-only. Analyze only campaign public evidence and robot geometry; never inspect object/contact truth, hidden state, evaluator internals, or unlisted experiment directories. Explicit transferred_self_experience sources in workspace.json are allowed public inputs.

Read workspace.json, canonical SKILL.md, and experience_read. Selectively retrieve this campaign's successful procedures, candidate waypoints and relative parameters from memory/experience.jsonl, memory/versions and cited public rollouts; do not dump the archive. Compare current RGB/state, adapt candidates, and verify every action. Never blindly replay. Use the exact Python interpreter in workspace.json; install nothing. Evidence is read-only; outputs require new descendants of the allowed rollout root.

## Observation and action

Call loco_start once with the supplied directory. Inspect available head RGB views, named measured/reference poses, joints and closure. No table plane or object dimensions are supplied. Independent resets retain learned skill.

Review one bounded waypoint from the latest observation, with fresh observation IDs, a unique scalebfm_act request ID and evidence-based reason. Follow returned next_call paths, including geometry calls. After every action compare fresh RGB and actual poses. Separate tracking, grasp progress, failures, and hypotheses. Targets, IK, closure, and timeouts prove neither grasp nor impossibility.

Continue until rollout_finished=true. After failure, change direction, clearance, orientation, step size, duration, or closure; never repeat unchanged failures.

## Four-point contract

Map by name: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. This is the public order. Never copy joint arrays positionally or output q29, torques, or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation; inactive components retain reference. Supplying measured quaternions alone does not activate tracking. Targets stay within 0.03 m and 0.10 rad of current measurement; duration 0.5-3 s. Feet normally retain support; arbitrary foot translations do not establish walking feasibility. ScaleBFM/native SIMPLE PD run at 50/200 Hz. Each episode permits 240 seconds of physical execution; simulation pauses while the model reasons. Wait for complete responses.

Grippers.left/right are ramped closure fractions: 0=open, 1=closed. Empty active lists permit gripper-only phases, not contact detection. Wrist links are not calibrated TCPs; import no foreign offsets. The SIMPLE hand uses a different collision mesh; prior capsule geometry is not supplied. Infer clearance from current images and measured robot poses. Do not copy prior task offsets or closure values without validation.

four_point_translate uses world XYZ metres; four_point_rotate uses world axis-angle radians and a pivot; four_point_place_local_point requires an explicit wrist-local point. Geometry tools calculate, never execute.

## Verification and transferred experience

This skill derives from grasp skill v14 after ten independent native grasp successes. Episodes437/438 each used25 actions, retrieved their own earlier public success, and verified current state before reuse. Their procedural lesson transfers: retrieve evidence, test bounded candidates, observe, correct, and record outcomes. Their cube-specific coordinates do not solve a door task. Read listed transfer sources selectively.

Ray-plane projection is not depth. Derive focal length from calibrated image height and vertical FOV. Use the stereo views and known camera calibration where correspondence is reliable; reject shadows, occlusion and inconsistent edges. Infer the moving door, frame, accessible push surface and free space from RGB.

Original-target holds can recover undertracking; reanchoring can accumulate drift. Isolated rotation or slower, smaller movement sometimes recovered tracking in grasp trials. Compare actual attitude with contact-time attitude. None is a universal remedy.

Establish gentle hand contact, test a small displacement and observe door motion relative to its frame. Continue bounded progress only when consistent. If contact slips, reposition from new images rather than repeat unchanged actions. A moving wrist, closed hand, or occluded handle does not prove success. Maintain support during any approach; arbitrary foot translations do not establish walking feasibility. Verify the full opening and one-second physical dwell, separating native success from the final visible state.

## Audit and learning

Distinguish local construction/analysis errors, explicit service errors, tracking timeouts, and uncertain transport. Preserve exact errors and layers. Await responses; use public receipts and experience_read before retries. Never replay uncertain or terminal actions, infer absent fields, or equate transport failure with physical failure. Explicit terminal wrappers override generic raw next_call text.

After success, budget end, or fault, read receipts/trajectory; submit the complete skill, concise lesson, and exact evidence paths through skill_update. Check every length cap. Keep learning separate from frozen evaluation; caps are ceilings, not targets.
