---
name: loco-manip-direct
description: Learn G1 DEX3 grasping before SIMPLE.
---

# Loco-manip Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. With either G1 DEX3 hand, grasp the red tabletop cube, lift it >=0.05 m above its episode-start height, and retain it >=0.5 s while standing. Preserve starting RGB. Require ten independent reset physical successes before SIMPLE door pushing.

Revise this skill, not weights; no demonstrations. Use registered services for physics; no second simulator or real robot. Existing environments/runtime remain read-only. Analyze only campaign public evidence and robot geometry; never inspect object/contact truth, hidden state, evaluator internals, or other experiments.

Read workspace.json, canonical SKILL.md, and experience_read. Selectively read earlier self-generated lessons by version/outcome in this campaign's memory/experience.jsonl, memory/versions, and cited public rollouts when useful; never dump the archive or replay coordinates. For NumPy/SciPy/PIL use exactly /home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python; install nothing. Evidence is read-only. Use designated scratch notes when writable; outputs require new descendants of the allowed rollout root.

## Observation and action

Call loco_start once with the supplied directory. Inspect head/wrist RGB, named measured/reference poses, joints, closure, and support plane. Reverify every reset; never replay historical poses.

Review one bounded waypoint from the latest observation, with a unique scalebfm_act request ID and evidence-based reason. Follow returned next_call paths, including geometry calls. After every action compare fresh RGB and actual poses. Separate measurements, tracking, grasp progress, failures, and hypotheses. Targets, IK, closure, and timeouts prove neither grasp nor impossibility.

Continue until rollout_finished=true, not merely turn completion. After failure, change direction, clearance, orientation, step size, duration, or closure; never repeat unchanged failures.

## Four-point contract

Map by name: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Public order is left wrist, right wrist, left ankle, right ankle. Never copy joint arrays positionally or output q29, torques, or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation; inactive components retain reference. Merely supplying measured quaternions does not activate tracking. Targets stay within 0.03 m and 0.10 rad of current measurement; duration 0.5-3 s. Feet normally retain support; arbitrary foot translations do not establish walking feasibility. ScaleBFM/PD run at 50/250 Hz.

Grippers.left/right are ramped closure fractions: 0=open, 1=closed. Empty active lists permit gripper-only phases, not contact detection. Wrist links are not calibrated TCPs; import no foreign offsets. Transform current finger capsule endpoints and radii into world coordinates. Check the entire hand through opening, closing, rotation, and translation. Clear the visible cube top before crossing; remeasure after closure.

four_point_translate uses world XYZ metres; four_point_rotate uses world axis-angle radians and a pivot; four_point_place_local_point requires an explicit wrist-local point. Geometry tools calculate, never execute.

## Verification and tested procedures

Ray-plane projection is not depth. Reject elevated corners, shadows, occlusion intersections, and inconsistent edges. Fit only RGB-supported dimensions; check residuals and both-view reprojections. Relocalize after interaction.

Isolated negative local-X rolls and smaller, slower approaches sometimes recover tracking. Original-target holds can recover undertracking; reanchoring can accumulate drift. Compare lifting attitude with grasp-time attitude and keep corrections bounded.

Test a 10-20 mm lift, then a separate hold. Verify cube/table motion in both views; wrist displacement or stable wrist RGB cannot prove cube rise. Rotated enclosure with a near-table corner is ambiguous: preserve closure through bounded verification. After confirmed loss, reopen with clearance and relocalize. Occlusion proves nothing. Complete the full height criterion and a >=0.5 s hold unless terminal.

Separate native success from endpoint retention; earlier native successes included table returns. Episode435's first .40 enclosure lost retention; its lower second .45 enclosure achieved native success with visible terminal enclosure. Depth, roll, alignment and closure changed together; no single cause is established. Both 15mm tests realized only ~7.5mm wrist rise; original-target holds recovered ~5-6mm. Low world-Y leveling partly tracked but timed out; always remeasure clearance. Attitude correction and local-Z experiments have not established a reliable retention remedy.

## Audit and learning

Distinguish local construction/analysis errors, explicit service errors, tracking timeouts, and uncertain transport. Preserve exact errors and layers in evidence. Await responses; use public receipts and experience_read before any retry. Never replay uncertain or terminal actions, infer absent fields, or equate transport failure with physical failure.

After success, budget end, or fault, read receipts/trajectory; submit the complete skill, concise lesson, and exact evidence paths through skill_update. Check every length cap, then return. Keep learning separate from frozen evaluation; caps are ceilings, not targets.
