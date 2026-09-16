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
standing. Preserve starting
RGB. Wrist targets and accumulated displacement cannot prove cube rise.
Ten independent reset physical successes precede SIMPLE door pushing.

Read workspace.json and canonical SKILL.md.
For NumPy/SciPy/PIL use exactly
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python. Install nothing.
Analyze only campaign public evidence and robot geometry. Never inspect
object/contact truth, hidden state, evaluator internals or other experiments.
Evidence is read-only. Use scratch/NOTES.md when writable; outputs require
new descendants of the allowed rollout root.

## Observe, act, verify

1. Read experience_read and current skill. Separate measurements, failures,
   supported procedures and hypotheses. Reverify every reset.
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
   duration or closure. Do not repeat unchanged failures or stop at model-turn end.
6. Test a 10-20 mm lift, then a separate hold. Verify cube motion against the
   table using both views; apparently stable wrist RGB can show a stationary cube.
   If retained, preserve closure, continue bounded lifts through the full height
   criterion, then hold at least 0.5 s unless the episode already terminated.
   Retained rotation is not loss; occlusion proves nothing.
   After confirmed loss, reopen with clearance and relocalize.

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
Clear the visible cube top before crossing it, not merely the table.
Historical closure geometry requires current verification.

four_point_translate uses world XYZ metres; four_point_rotate uses world
axis-angle radians and a pivot; four_point_place_local_point needs an explicit
wrist-local point. Geometry tools calculate, never execute.
Ray-plane projection is not object depth. Reject elevated-corner projections,
inconsistent edge lengths and ambiguous matches. Small ray mismatch alone is
insufficient with weak baselines. Relocalize after interaction.

## Evidence and next reset

Episodes 1-2 exhausted budgets. Brief co-motion at closure .5 later slipped;
stronger .6/.65 regrasp also failed. More closure is not necessarily better.
Orientation-only control drifted 37 mm; explicit position holds improved it.
Episode 3 succeeded with .2/.35/.45 closure, a test lift, separate hold and further lifts.

Episode 4 recorded native success; terminal RGB suggests return to table: 0042 matched visible top corners near .679-.680 m and a bottom corner
near .631 m. Report native success separately from endpoint retention.
Precontact rolls tracked better when isolated after combined-motion timeouts.
Descent orientation drift reduced .2 finger-table clearance to 6 mm; a requested
12 mm rise yielded only 5 mm, so remeasure even after target_reached.
The first .45 grasp's stable wrist view misled: 0030 stereo
put cube top near .675-.678 m on the table. Reopen and recenter after loss.
The second grasp used lower side contact: .35 thumb z about .673 m versus
.683 m initially, with about 15 mm minimum table clearance. Preserve .45
through the 15 mm test, separate 2 s hold and three 20 mm lifts. Wrist rises
13.5/18/21/21 mm are tracking evidence; native success was saved in call_0044.
Improved contact depth remains a hypothesis.

## Learn between attempts

After success, budget end or fault, read public receipts and trajectory. Episodes 3-4 terminal serialization failed after saved
success; experience_read directed skill_update. Never replay terminal actions.
Submit complete revised skill, lesson and exact evidence paths through
skill_update; check all length caps. The host archives versions and resets. Keep skill learning separate from frozen evaluation.
Submit and return.
