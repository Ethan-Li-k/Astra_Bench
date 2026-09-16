---
name: loco-manip-direct
description: Learn G1 DEX3 visual grasping through registered four-point trials and evidence-backed skill revision before SIMPLE.
---

# Loco-manip Direct policy

Always use gpt-6-astra/xhigh. Learn by revising this skill, not weights.
No demonstrations. All physics uses registered services; no second simulator
or real robot. Existing environments and runtime code remain read-only.

## Task and completion

Use either G1 DEX3 hand to grasp the red tabletop cube, lift the cube at least
0.05 m above its episode-start height, and retain the grasp for at least 0.5 s
while the humanoid remains standing. These are requirements, not object
measurements. Preserve the starting RGB evidence. Verify actual cube rise;
wrist targets or accumulated wrist displacement do not establish cube height.
Ten independent reset physical grasp successes are required before SIMPLE
door pushing.

Read workspace.json. Analyze only campaign public evidence and robot geometry.
Never inspect object/contact truth, hidden state, evaluator internals or other
experiments. Evidence is read-only. Use scratch/ and NOTES.md when writable;
service outputs require new descendants of the allowed rollout root.

## Observe, act, verify

1. Read experience_read and current SKILL.md. Separate measured facts,
   failed attempts, supported procedures and hypotheses. Reverify each reset.
2. Call loco_start once with the supplied directory. Inspect head/wrist RGB,
   named measured/reference poses, named joints, gripper commands and supplied
   support-plane calibration.
3. Review one bounded waypoint from the latest observation. Use a unique
   scalebfm_act request ID and evidence-based reason. Follow returned next_call
   paths, including after geometry calls. Never replay uncertain actions.
4. Compare fresh RGB and actual poses after every action. Assess tracking and
   task progress separately. Targets, IK, closure and timeouts prove neither
   grasp nor impossibility. Retract conclusions contradicted by later evidence.
5. Continue until rollout_finished=true, including after timeouts. Change an
   evidence-supported direction, clearance, orientation, step size, duration
   or closure after failure. Do not repeat unchanged failures or stop physics
   because inference is slow or a model turn ends.
6. Test a 10-20 mm lift, then a separate hold; if grasp is retained, preserve
   closure and continue bounded lifts to the full height criterion, then hold
   at least 0.5 s. Occlusion alone is insufficient. Distinguish small retained
   rotation from actual loss; do not release solely because orientation changes.
   After confirmed loss, reopen with clearance and relocalize.

## Four-point contract

Map by name: left_wrist_yaw_link, right_wrist_yaw_link,
left_ankle_roll_link, right_ankle_roll_link. Public order is left wrist,
right wrist, left ankle, right ankle. Never copy joint arrays across interfaces
without named mapping. Do not output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses.
Declare active.position and active.orientation. Inactive components retain
reference; supplying measured quaternions does not activate tracking.
Each target is within 0.03 m and 0.10 rad of current measurement.
Duration is 0.5-3 s. Use one waypoint, then reobserve. Feet normally retain
support; arbitrary foot translations do not establish feasible walking.
ScaleBFM runs at 50 Hz, PD at 250 Hz.

Grippers.left/right are closure fractions: 0=open, 1=closed, ramped over duration.
Empty active lists permit gripper-only phases, not contact detection.
Wrist links are not calibrated grasp TCPs. Never import other robots' offsets.
Transform current finger capsule endpoints and radii into world coordinates;
check the whole hand through opening, closing, rotation and translation.
Clear the visible cube top before crossing it, not merely the table plane.

four_point_translate uses world XYZ metres. four_point_rotate uses world
axis-angle radians and a pivot. four_point_place_local_point requires an
explicit wrist-local point. Geometry tools calculate, never execute.
Ray-plane projection is not object depth. Tilted/elevated bottom corners may
not touch the table. Reject inconsistent edge lengths and ambiguous stereo
matches; inspect ray mismatch and relocalize after interaction.

## Evidence and next trial

No complete grasp procedure is verified. Episode 1 showed 26 mm wrist-lift
co-motion at closure 0.5, then slip during another 25 mm lift; a 0.65 regrasp
also lost the cube.

Episode 2 precontact rolls reduced paired-finger height separation. A rotation
with inactive position drifted about 37 mm; explicit position holds improved
tracking. Table clearance still allowed possible cube contact during approach.
Staged closure 0.2/0.35/0.5 preceded a measured 13 mm wrist lift and 2 s hold.
The cube remained visible between fingers but rotated; declaring failure from
rotation alone was unjustified. Full height/retention success was unverified.
A lower recentered regrasp followed by closure 0.6 displaced the cube downward;
after reopening, RGB showed it on the floor. Stronger closure is not proven better.

Recovery initially undertracked, including position-only and bilateral trials.
Some timeouts had good vertical tracking but poor orientation. Isolated
reorientation and later longer forward/downward motions restored partial
descent; the last three descents measured about 14/18/19 mm. 
## Learn between attempts

After success, budget end or physics/transport fault, read outcome and public
trajectory. Submit the complete revised skill, lesson and exact evidence paths
with skill_update; check all length caps. The host archives versions.
Episodes 1 and 2 ended at the step budget with native_outcome=in_progress and
zero native successes. Keep learning separate from frozen evaluation.
Submit and return; the host continues independent resets.
