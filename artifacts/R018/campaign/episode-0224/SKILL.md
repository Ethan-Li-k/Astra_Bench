---
name: loco-manip-direct
description: Learn G1 DEX3 grasping before SIMPLE.
---

# Loco-manip Direct policy

Always use gpt-6-astra/xhigh. Revise this skill, not weights. No demonstrations.
All physics uses registered services; no second simulator or real robot.
Existing environments and runtime code remain read-only.

## Task and runtime

Use either G1 DEX3 hand to grasp the red tabletop cube, lift the cube at least
0.05 m above its episode-start height, and retain it for at least 0.5 s while
standing. Preserve starting RGB. Wrist displacement cannot prove cube rise.
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
   named measured/reference poses, named joints, gripper commands and support
   plane calibration.
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
right wrist, left ankle, right ankle. Never copy joint arrays across interfaces
without named mapping. Do not output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses.
Declare active.position and active.orientation. Inactive components retain
reference; measured quaternion fields alone do not activate tracking.
Each target stays within 0.03 m and 0.10 rad of current measurement.
Duration is 0.5-3 s. One waypoint, then reobserve. Feet normally retain support;
arbitrary foot translations do not establish feasible walking.
ScaleBFM runs at 50 Hz, PD at 250 Hz.

Grippers.left/right are closure fractions: 0=open, 1=closed, ramped over duration.
Empty active lists permit gripper-only phases, not contact detection.
Wrist links are not calibrated TCPs. Never import other robots' offsets.
Transform current finger capsule endpoints and radii into world coordinates.
Check the whole hand through opening, closing, rotation and translation.
Clear the visible cube top before crossing it. Reverify closure geometry.
Explicit position holds reduce orientation-only drift; reanchoring each step
can accumulate drift. Compare lifting attitude with grasp-time attitude.

four_point_translate uses world XYZ metres; four_point_rotate uses world
axis-angle radians and a pivot; four_point_place_local_point requires an explicit
wrist-local point. Geometry tools calculate, never execute.
Ray-plane projection is not object depth. Reject elevated-corner projections,
inconsistent edges, shadow boundaries and occlusion intersections.
Fit visible dimensions only when supported by RGB; resolve pose/sign ambiguity
using the other view. Relocalize after interaction.

## Evidence and hypotheses

Episodes 1-2 exhausted budgets; .5 slipped and .6/.65 did not fix retention.
Episodes 3-7 recorded native success with .2/.35/.45 closure;
endpoints 4-7 supported table return.

Episode 7 enclosure failed despite fixed grasp quaternion.
Relocalization, retraction and 27 mm open descent tracked. Predicted .35
clearance was 8 mm; raising 7 mm during closure left minimum .646 m.
Second grasp preserved .45 through test15 mm, separate2 s hold and
20/20/15 mm lifts. Grasp-attitude deviations at0032-0035 were
.011/.022/.040/.081 rad, versus episode6 cumulative .184 rad.
0035 native success returned; six-corner fit gave center .654 m,
minimum .629 m, RMS .22 px, and both views supported table return.
Smaller drift alone did not secure endpoint retention. Occluded intermediate
faces did not establish full height. Reject mixed-height pairs, shadow
vertices and inconsistent face fits; verify corners against outer contour.

## Audit and learning

Distinguish pre-execution parse errors, explicit service errors, tracking
timeouts and executed actions with uncertain retention.
Preserve exact error text and layer. Await complete tool responses; use public
receipts and experience_read to establish execution before any retry.
Episodes 3-5 serialization-failure claims are unverified; user audit reports
successful host completion with error=null. Never present remembered transport
errors as verified host failures.

After success, budget end or fault, read public receipts and trajectory.
Never replay terminal actions. Submit complete revised skill, lesson and exact
evidence paths through skill_update; check all length caps. Keep skill learning separate from frozen evaluation.
Submit and return.
