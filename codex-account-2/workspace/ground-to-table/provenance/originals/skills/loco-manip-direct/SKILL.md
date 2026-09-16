---
name: loco-manip-direct
description: Learn G1 DEX3 grasping before SIMPLE.
---

# Loco-manip Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. With either G1 DEX3 hand, grasp the red tabletop cube, lift it >=0.05 m above its episode-start height, and retain it >=0.5 s while standing. Preserve starting RGB. Require ten independent reset physical successes before SIMPLE door pushing. This is fixed-reset self-experience learning; host diagnostic replays do not count as policy trials.

Revise this skill, not weights; no demonstrations. Use registered services for physics; no second simulator or real robot. Existing environments/runtime remain read-only. Analyze only campaign public evidence and robot geometry; never inspect object/contact truth, hidden state, evaluator internals, or other experiments.

Read workspace.json, canonical SKILL.md, and experience_read. Selectively retrieve this campaign's successful procedures, candidate waypoints and relative parameters from memory/experience.jsonl, memory/versions and cited public rollouts; do not dump the archive. Compare current RGB/state, adapt candidates, and verify every action. Never blindly replay. For NumPy/SciPy/PIL use exactly /home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python; install nothing. Evidence is read-only. Use designated scratch notes when writable; outputs require new descendants of the allowed rollout root.

## Observation and action

Call loco_start once with the supplied directory. Inspect head/wrist RGB, named measured/reference poses, joints, closure and support plane. Independent resets retain learned skill.

Review one bounded waypoint from the latest observation, with fresh observation IDs, a unique scalebfm_act request ID and evidence-based reason. Follow returned next_call paths, including geometry calls. After every action compare fresh RGB and actual poses. Separate tracking, grasp progress, failures, and hypotheses. Targets, IK, closure, and timeouts prove neither grasp nor impossibility.

Continue until rollout_finished=true. After failure, change direction, clearance, orientation, step size, duration, or closure; never repeat unchanged failures.

## Four-point contract

Map by name: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. This is the public order. Never copy joint arrays positionally or output q29, torques, or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation; inactive components retain reference. Supplying measured quaternions alone does not activate tracking. Targets stay within 0.03 m and 0.10 rad of current measurement; duration 0.5-3 s. Feet normally retain support; arbitrary foot translations do not establish walking feasibility. ScaleBFM/PD run at 50/250 Hz.

Grippers.left/right are ramped closure fractions: 0=open, 1=closed. Empty active lists permit gripper-only phases, not contact detection. Wrist links are not calibrated TCPs; import no foreign offsets. Transform current finger capsule endpoints and radii into world coordinates. Check entire capsules through opening, closing, rotation, and translation. Clear the visible cube top before crossing; remeasure after closure.

four_point_translate uses world XYZ metres; four_point_rotate uses world axis-angle radians and a pivot; four_point_place_local_point requires an explicit wrist-local point. Geometry tools calculate, never execute.

## Verification and tested procedures

Ray-plane projection is not depth. Derive focal length from calibrated image height and vertical FOV. Reject elevated corners, shadows, occlusion intersections, and inconsistent edges. Fit only RGB-supported dimensions; check residuals and both-view reprojections. Relocalize after interaction, including table margin; repeated failed contacts can push the cube off the edge.

Isolated negative local-X rolls and smaller, slower approaches sometimes recover tracking. Original-target holds can recover undertracking; reanchoring can accumulate drift. Compare lifting attitude with grasp-time attitude and keep corrections bounded.

Test a 10-20 mm lift, then a separate hold. Verify cube/table motion in both views; wrist displacement or stable wrist RGB cannot prove cube rise. Ambiguous tilted enclosure warrants bounded verification with closure retained. After confirmed loss, reopen with clearance and relocalize. Complete the height criterion and >=0.5 s hold unless terminal.

437/438 each reached native success in25 actions; retrieve their0017-0025 geometry/targets as candidates. 438 matched437's reset.15mm horizontal/-.09roll omitted the failed upward component;25mm then timed out,20mm/-.08 recovered. High .20 alignment used six bounded relative rotations toward437/0019 with2-4mm rise compensation, then29/16mm descents, stationary.35/.45 closure, test15mm, independent1.5s original-target hold, and20/20mm rises.437 used29/14mm descents.436's.45/.50/.55 failures show stronger closure is no proven remedy. Depth, alignment, roll and closure interact; no single causal fix is established. Separate native success, endpoint retention, visual height uncertainty, and independently observed hold duration.

## Audit and learning

Distinguish local construction/analysis errors, explicit service errors, tracking timeouts, and uncertain transport. Preserve exact errors and layers. Await responses; use public receipts and experience_read before retries. Never replay uncertain or terminal actions, infer absent fields, or equate transport failure with physical failure. Explicit terminal wrappers override generic raw next_call text.

After success, budget end, or fault, read receipts/trajectory; submit the complete skill, concise lesson, and exact evidence paths through skill_update. Check every length cap. Keep learning separate from frozen evaluation; caps are ceilings, not targets.
