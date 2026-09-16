---
name: loco-manip-direct
description: Learn G1 DEX3 visual grasping through registered four-point trials and evidence-backed skill revision before SIMPLE.
---

# Loco-manip Direct policy

Always use gpt-6-astra/xhigh. Revise this skill, not weights. No demonstrations.
All physics uses registered services; no second simulator or real robot.
Existing environments and runtime code remain read-only.

## Task and runtime

Use either G1 DEX3 hand to grasp the red tabletop cube, lift the cube at least
0.05 m above its episode-start height, and retain it for at least 0.5 s while
standing. These are requirements, not object measurements. Preserve starting
RGB. Verify cube rise; wrist targets or accumulated displacement cannot prove
cube height. Ten independent reset physical successes precede SIMPLE door pushing.

Read workspace.json and its canonical SKILL.md; agent/SKILL.md may be the
episode-start copy. For NumPy/SciPy/PIL analysis use exactly
/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python.
Do not install packages.
Analyze only campaign public evidence and robot geometry. Never inspect
object/contact truth, hidden state, evaluator internals or other experiments.
Evidence is read-only. Use scratch/NOTES.md when writable; outputs
require new descendants of the allowed rollout root.

## Observe, act, verify

1. Read experience_read and current skill. Separate measurements, failures,
   supported procedures and hypotheses. Reverify each reset.
2. Call loco_start once with the supplied directory. Inspect head/wrist RGB,
   named measured/reference poses, named joints, gripper commands and support
   plane calibration.
3. Review one bounded waypoint from the latest observation. Use a unique
   scalebfm_act request ID and evidence-based reason. Follow returned next_call
   paths, including geometry calls. Never replay uncertain actions.
4. Compare fresh RGB and actual poses after every action. Assess tracking
   separately from grasp progress. Targets, IK, closure and timeouts prove
   neither grasp nor impossibility. Retract contradicted conclusions.
5. Continue until rollout_finished=true, including after timeouts. After failure,
   change an evidence-supported direction, clearance, orientation, step size,
   duration or closure. Do not repeat unchanged failures or stop because
   inference is slow or a model turn ends.
6. Test a 10-20 mm lift, then a separate hold. If retained, preserve closure,
   continue bounded lifts through the full height criterion, then hold at least
   0.5 s. Occlusion alone is insufficient. Small retained rotation is not loss.
   After confirmed loss, reopen with clearance and relocalize.

## Four-point contract

Map by name: left_wrist_yaw_link, right_wrist_yaw_link,
left_ankle_roll_link, right_ankle_roll_link. Public order is left wrist,
right wrist, left ankle, right ankle. Never copy joint arrays across interfaces
without named mapping. Do not output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses.
Declare active.position and active.orientation. Inactive components retain
reference; supplying measured quaternions does not activate tracking.
Each target stays within 0.03 m and 0.10 rad of current measurement.
Duration is 0.5-3 s. One waypoint, then reobserve. Feet normally retain support;
arbitrary foot translations do not establish feasible walking.
ScaleBFM runs at 50 Hz, PD at 250 Hz.

Grippers.left/right are closure fractions: 0=open, 1=closed, ramped over duration.
Empty active lists allow gripper-only phases, not contact detection.
Wrist links are not calibrated TCPs. Never import other robots' offsets.
Transform current finger capsule endpoints and radii into world coordinates;
check the whole hand through opening, closing, rotation and translation.
Clear the visible cube top before crossing it, not merely the table plane.

four_point_translate uses world XYZ metres; four_point_rotate uses world
axis-angle radians and a pivot; four_point_place_local_point needs an explicit
wrist-local point. Geometry tools calculate, never execute.
Ray-plane projection is not object depth. Reject elevated-corner projections,
inconsistent edge lengths and ambiguous matches. Check ray mismatch and
relocalize after interaction.

## Evidence and next reset

Episodes 1-2 exhausted budgets without native success. Closure 0.5 gave short
co-motion; later slip and stronger 0.6/0.65 regrasp failures showed that more
closure is not necessarily better. Rotation alone previously prompted an
unjustified release. Orientation-only control drifted 37 mm; explicit position
holds improved tracking.

Episode 3 recorded native_outcome=success. Reverify every reset. Raise with clearance, apply bounded negative wrist-local-x rolls
with position active, then approach above the cube. Isolating roll improved
tracking after combined rise/roll timeouts. Align paired-finger heights before
descending. Public RGB triangulation in 0012/0013 gave top about 0.681 m and
49 mm edges; an 81 mm table projection was rejected.

At closure 0.2, finger-table clearance was only 3 mm; raising/recentering
increased it to about 14 mm. Stages 0.2/0.35/0.45 enclosed the cube. Preserve
0.45 despite retained rotation: a 15 mm test request gave 8 mm wrist rise,
followed by a separate 2 s hold and three 20 mm requests giving 18/18/19 mm
wrist rises. RGB retained the cube above the table; native success reports
completion. Wrist rises are tracking evidence, not independent cube heights.
Final center-height fitting was ambiguous under occlusion.

## Learn between attempts

After success, budget end or physics/transport fault, read public outcome and
trajectory. Episode 3 terminal serialization failed, but saved call_0026
reported success and experience_read directed skill_update. Read saved receipts
and next_call; never replay terminal actions.
Submit the complete revised skill, lesson and exact evidence paths through
skill_update; check all length caps. The host archives versions and continues
independent resets. Keep skill learning separate from frozen evaluation.
Submit and return.
