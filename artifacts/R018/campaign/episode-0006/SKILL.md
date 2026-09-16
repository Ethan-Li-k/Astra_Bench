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
5. Continue until rollout_finished=true, including after timeouts. After failure,
   change an evidence-supported direction, clearance, orientation, step size,
   duration or closure. Do not repeat unchanged failures or stop at turn end.
6. Test a 10-20 mm lift, then a separate hold. Compare cube motion against the
   table using both views. Stable wrist RGB can show a stationary cube.
   A rotated short-test grasp with a near-table corner is ambiguous, not confirmed
   loss. Preserve closure through further bounded verification if still enclosed.
   If retained, complete the full height criterion, then hold at least 0.5 s
   unless terminal. After confirmed loss, reopen with clearance and relocalize.
   Occlusion proves nothing. Report native success separately from endpoint retention.

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
Clear the visible cube top before crossing it. Historical closure geometry
requires current verification. Repeated measured-position holds can accumulate drift.

four_point_translate uses world XYZ metres; four_point_rotate uses world
axis-angle radians and a pivot; four_point_place_local_point needs an explicit
wrist-local point. Geometry tools calculate, never execute.
Ray-plane projection is not object depth. Reject elevated-corner projections,
inconsistent edges and ambiguous matches. Fit visible dimensions only when
supported by RGB; resolve pose/sign ambiguity using the other view.
Do not treat occlusion intersections as corners. Relocalize after interaction.

## Evidence and next reset

Episodes 1-2 exhausted budgets; .5 slipped and .6/.65 did not fix retention.
Explicit position holds improved orientation-only drift. Episodes 3-5 recorded
native success with staged .2/.35/.45 closure; episode 4 endpoint indicated table return.

Episode 5 high-clearance negative local-x rolls tracked, including later
combined approaches. Negative world-Y rotations raised long fingers relative
to thumb at high wrist positions, but low-position correction timed out.
Descent drift reached .12 rad despite accurate position. Flatter/lower contact
remains a hypothesis, not an established improvement.

0021 visible vertical edges supported top .679 m and 49.6-50.9 mm edges.
The first test/hold fit had minimum .629 m; reopening on this alone was premature.
Second grasp preserved .45 through a 15 mm test, separate 2 s hold and two
20 mm lifts. 0041/0042 visible-face fits checked against head RGB supported
center .687/.707 m, minimum .652/.673 m. Final 2 s hold saved native success,
but 0043 multiview fitting supported center .667 m and minimum .631 m:
the cube returned to table. Transient lift and endpoint retention differ.

## Learn between attempts

After success, budget end or fault, read public receipts and trajectory.
Episodes 3-5 terminal serialization failed after saved success; experience_read
directed skill_update. Never replay terminal actions.
Submit complete revised skill, lesson and exact evidence paths through
skill_update; check all length caps. The host archives versions and resets.
Keep skill learning separate from frozen evaluation. Submit and return.
