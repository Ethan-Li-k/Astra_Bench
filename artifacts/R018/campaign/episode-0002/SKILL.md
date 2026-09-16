---
name: loco-manip-direct
description: Learn humanoid visual grasping through autonomous ScaleBFM four-point trials, evidence-based skill revision and persistent experience, then transfer to SIMPLE.
---

# Loco-manip Direct policy

Operate as GPT-6 Astra/xhigh from RGB, measured state, task and experience.
Learning revises this skill, not weights. Preserve the task. No demonstrations.
All physics uses registered services; no second simulator or real robot.
Existing environments and runtime code remain read-only.

Read workspace.json. Analyze only campaign public evidence and robot geometry.
Never inspect object/contact truth, hidden state, evaluator internals or other
experiments. Evidence is read-only. Use scratch/ and NOTES.md when writable;
service outputs require new descendants of the allowed rollout root.

## Observe, act, verify

1. Read experience_read and the current SKILL.md. Separate measured facts,
   failed attempts, successful procedures and untested hypotheses. Reverify experience each reset.
2. Call loco_start once with the supplied fresh directory. Inspect head/wrist
   RGB, named measured/reference poses, named joints and gripper commands.
   Read the supplied support-plane calibration.
3. Review one bounded waypoint from the latest observation. Call scalebfm_act
   with a unique request ID and evidence-based reason. Follow next_call paths,
   including after geometry calls. Never guess paths or replay uncertain actions.
4. Compare RGB and actual poses before/after each action. Assess tracking and
   task progress separately. Targets, IK, closure and timeouts prove neither
   grasp nor impossibility. Retract subgoals contradicted by later evidence.
5. Continue until rollout_finished=true, including after timeouts. Change an
   evidence-supported direction, clearance, orientation, step size, duration or
   closure when an approach fails. Do not repeat unchanged failures or end the
   physical episode because a model turn ends.
6. Verify cube co-motion during a short lift, then a separate hold, then further
   lift and hold. Preserve intended closure. Occlusion or transient co-motion
   alone is insufficient. After slip, reopen with clearance and relocalize.

## Four-point contract

G1 with DEX3. Map by name: left_wrist_yaw_link, right_wrist_yaw_link,
left_ankle_roll_link, right_ankle_roll_link. Public order is left wrist,
right wrist, left ankle, right ankle; never copy joint arrays across interfaces
without named mapping. Do not output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses.
Declare active.position and active.orientation. Inactive components retain
reference; supplying measured quaternions does not activate tracking.
Each target is within 0.03 m and 0.10 rad of its current measurement.
Duration is 0.5-3 s. Use one waypoint, then reobserve. Feet normally retain
support; arbitrary foot translation does not establish feasible walking.
ScaleBFM runs at 50 Hz, PD at 250 Hz.

Grippers.left/right are closure fractions: 0=open, 1=closed, ramped over the
waypoint duration. Empty active lists permit gripper-only phases, not contact
detection. Wrist links are not calibrated grasp TCPs (tool center points).
Never import other robots' offsets.

four_point_translate uses world XYZ metres. four_point_rotate uses world
axis-angle radians and a pivot; rotating a wrist moves offset fingers.
four_point_place_local_point requires an explicitly declared wrist-local point.
Geometry tools calculate, never execute.

## Geometry and evidence from episode 1

No grasp procedure is verified. Raising the wrist before
approach established clearance. Empty half-closure exposed opposing geometry. Read current finger capsule endpoints and radii; transform
them into world coordinates. Check the entire hand, not only the wrist.

Initial orientation left one finger low while the thumb stayed high. Small local-x rolls reduced
their world-height difference; several 2 s roll steps tracked well. Rolling
while already near the cube also displaced it. Next attempt: establish the
orientation behind the table edge before approaching. This is untested.

image_pixel_to_world_plane gives a ray-plane intersection, not object depth.
A visible bottom corner need not touch the table if the cube tilts or lifts.
Reject inconsistent projected edge lengths or ambiguous stereo matches.
Use matching features across fresh calibrated views and inspect ray mismatch.
Relocalize after contact; do not memorize this episode's object coordinates.

At closure 0.5, RGB showed co-motion with a measured 26 mm wrist lift.
During the next 25 mm lift the cube slipped back to the table. A subsequent
lower approach with closure 0.65 also lost the cube; later wrist RGB located
it below the table on the floor.
Next discriminating trial: verify opposing enclosure away from the edge,
close in stages, make a 10-20 mm lift, and hold before increasing height.
Compare cube-hand motion during closure to detect pushing or ejection.

Recovery descents undertracked despite retraction, duration changes and a
bilateral-wrist test. Inspect position and rotation errors separately;
some lift timeouts had good position tracking. Rebase subsequent bounded targets on measurements.

## Learn between attempts

After success, budget end or physics/transport fault, read outcome and trajectory.
Preserve evidence; never replay uncertain actions. Submit the complete revised
skill, lesson and exact evidence paths with skill_update. Check all length caps.
The host archives versions. Retain facts and distinguish hypotheses.

Episode 1 ended at the step budget with native_outcome=in_progress and zero
successes. The host continues independent resets. Ten native physical grasp successes
unlock SIMPLE; repeated frames/replays do not count. Episode failure is not
campaign completion. Separate learning from frozen evaluation. Submit the update,
then return. Use concise public explanations.
