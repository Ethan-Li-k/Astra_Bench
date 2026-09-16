---
name: loco-manip-direct
description: Learn G1 DEX3 grasping before SIMPLE.
---

# Loco-manip Direct policy

Always use gpt-6-astra/xhigh. Revise this skill, not weights. No demonstrations.
All physics uses registered services; no second simulator or real robot.
Existing environments and runtime code remain read-only.

## Task and runtime

With either G1 DEX3 hand, grasp the red tabletop cube, lift it >=0.05m above
its episode-start height and retain it >=0.5s while standing. Preserve starting RGB. Wrist displacement cannot prove cube rise.
Ten independent reset physical successes precede SIMPLE door pushing.

Read workspace.json, canonical SKILL.md and experience_read.
For NumPy/SciPy/PIL use exactly
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python. Install nothing.
Analyze only campaign public evidence and robot geometry. Never inspect
object/contact truth, hidden state, evaluator internals or other experiments.
Evidence is read-only. Use scratch/NOTES.md when writable; outputs require
new descendants of the allowed rollout root.

## Observe, act, verify

1. Separate measurements, failures, supported procedures and hypotheses.
   Reverify every reset; historical poses are not replay targets.
2. Call loco_start once with the supplied directory. Inspect head/wrist RGB,
   named measured/reference poses, joints, gripper commands and support plane.
3. Review one bounded waypoint from the latest observation. Use a unique
   scalebfm_act request ID and evidence-based reason. Follow returned next_call
   paths, including geometry calls. Never replay uncertain actions.
4. Compare fresh RGB and actual poses after every action. Tracking is separate
   from grasp progress. Targets, IK, closure and timeouts prove neither grasp
   nor impossibility. Retract conclusions contradicted by new evidence.
5. Continue until rollout_finished=true, including after tracking timeouts.
   After failure, change direction, clearance, orientation, step size, duration
   or closure using evidence. Never repeat unchanged failures.
6. Test a 10-20 mm lift, then a separate hold. Compare cube/table motion in both
   views. Stable wrist RGB can show a stationary cube. A rotated short-test
   enclosure with a near-table corner is ambiguous, not confirmed loss.
   Preserve closure through bounded verification while still enclosed.
   Complete the full height criterion, then hold at least 0.5 s unless terminal.
   After confirmed loss, reopen with clearance and relocalize. Occlusion proves
   nothing. Report native success separately from endpoint retention.

## Four-point contract

Map by name: left_wrist_yaw_link, right_wrist_yaw_link,
left_ankle_roll_link, right_ankle_roll_link. Public order is left wrist,
right wrist, left ankle, right ankle. Never copy joint arrays without named mapping. Do not output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses.
Declare active.position and active.orientation. Inactive components retain
reference; measured quaternion fields alone do not activate tracking.
Each target stays within 0.03 m and 0.10 rad of current measurement.
Duration is 0.5-3 s. One waypoint, then reobserve. Feet normally retain support;
arbitrary foot translations do not establish feasible walking.
ScaleBFM/PD run at50/250 Hz.

Grippers.left/right are closure fractions: 0=open, 1=closed, ramped over duration.
Empty active lists permit gripper-only phases, not contact detection.
Wrist links are not calibrated TCPs. Never import other robots' offsets.
Transform current finger capsule endpoints and radii into world coordinates.
Check the whole hand through opening, closing, rotation and translation.
Clear the visible cube top before crossing it. Reverify closure geometry.
Position holds reduce drift; reanchoring can accumulate it.
Compare lifting attitude with grasp-time attitude.

four_point_translate uses world XYZ metres; four_point_rotate uses world
axis-angle radians and a pivot; four_point_place_local_point requires an explicit
wrist-local point. Geometry tools calculate, never execute.
Ray-plane projection is not depth. Reject elevated corners, inconsistent
edges, shadows and occlusion intersections.
Fit only RGB-supported dimensions; resolve pose/sign ambiguity with both
views. Relocalize after interaction.

## Evidence and hypotheses

Episodes1-2 exhausted budgets. Episodes3-7 recorded native success;
endpoints4-7 supported table return.
Episode432: isolated rolls recovered after combined-motion timeouts.
Second .40 enclosure reached native success; terminal fit supported
center.7082,min.6692m,
about53mm rise; no later hold.

Episode433: isolated rolls and slower horizontal approach recovered tracking.
First .40 enclosure failed after test15/hold/20/20; correct five-corner0022
fit gave center.6551,min.6299m,RMS.61px. Incorrect silhouette correspondences
were rejected. Second approach changed alignment and depth.
At0029 thumb/index/middle centers were .6729/.6574/.6503m, radii10mm.
Same .40, test15/hold/20/20/hold/15 recorded native success. Final attitude
error grew from.049 to.113rad despite accurate position. Terminal0035
multiview fit RMS.49px,center.6541,min.6285m and separation support table
return. Lower contact and .40 did not secure endpoint retention.
Pre-ascent attitude correction remains an untested hypothesis.

## Audit and learning

Distinguish pre-execution parse errors, explicit service errors, tracking
timeouts and executed actions with uncertain retention.
Preserve exact errors and layers. Await responses; use public receipts and
experience_read to establish execution before any retry.
Episodes3-5 serialization claims remain unverified. Episodes432/433 functions
serialization errors did not negate public native success; experience_read
directed skill_update. Do not infer absent fields.
Never infer physical failure from transport errors or replay terminal actions.

After success, budget end or fault, read public receipts and trajectory.
Submit complete skill, lesson and exact evidence paths through skill_update;
check all length caps. Keep learning separate from
frozen evaluation.
Submit and return.
