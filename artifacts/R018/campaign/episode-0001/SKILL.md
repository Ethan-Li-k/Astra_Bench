---
name: loco-manip-direct
description: Learn humanoid visual grasping through autonomous ScaleBFM four-point trials, evidence-based skill revision and persistent experience, then transfer to SIMPLE.
---

# Loco-manip Direct policy

Operate as GPT-6 Astra/xhigh, the autonomous policy. Choose your own actions
from RGB, measured robot state, task instruction and recorded experience.
Normal calculation, image inspection, crops, scripts and notes remain available.
Service tools control physics; never open a second simulator connection.
There is no pi0.5 proposal or human demonstration. Learning means improving
this skill and your experience, not changing GPT weights.

`workspace.json` supplies the interpreter, permitted evidence paths, task and
current skill version. Write analysis in `scratch/` and progress in `NOTES.md`.
Recorded evidence and runtime code are read-only. Never inspect object truth,
contact truth, evaluator internals, hidden state or unrelated experiment files.

## Observe, act, verify

1. Read `experience_read` and your current skill. Distinguish measured facts,
   successful procedures, failed attempts and untested hypotheses. Experience
   from another attempt is guidance, not proof about the current scene.
2. Call `loco_start` once with the supplied fresh output directory. Inspect
   head and wrist RGB, current named four-point poses, reference poses, joint
   state and gripper commands. Derive the needed subgoals from the task.
3. Choose one bounded waypoint. Use geometry tools or analysis code to compute
   transforms. Call `scalebfm_act` with the latest observation path, a unique
   request ID and a brief evidence-based reason. Follow returned `next_call`
   paths; never guess file names or retry uncertain execution.
4. Compare before/after images and measured poses with the request. Assess
   separately what actually happened and whether the next action advances a
   valid prerequisite. Retract a completed subgoal when new evidence disagrees.
   A target, IK solution, closed hand or timeout alone proves neither grasp
   nor geometric impossibility. Verify object motion while lifting and holding.
5. Continue while `rollout_finished=false`, including after tracking timeouts.
   Change an evidence-supported aspect of a failing approach: direction,
   clearance, orientation, step size, duration or closure. Do not repeat an
   unchanged failure indefinitely or stop just because success seems unlikely.

## Four-point contract

Robot: G1 with DEX3. Public order is left wrist, right wrist, left ankle,
right ankle: `left_wrist_yaw_link`, `right_wrist_yaw_link`,
`left_ankle_roll_link`, `right_ankle_roll_link`. Every waypoint includes all
four absolute `position_world_m` and unit `quaternion_wxyz` poses. Map by name.
These are link frames, not calibrated grasp TCPs. TCP means tool center point.
Do not import Panda/X5 offsets; infer hand clearance from allowed geometry/RGB.

Declare `active.position` and `active.orientation` names. Only active components
change; inactive components keep their reference. Keeping a measured quaternion
does not activate orientation tracking. Each target is within 0.03 m/0.10 rad
of current measurement; duration is 0.5–3 s. Use one waypoint before reobserving.
Feet normally retain support while manipulating; arbitrary foot translation
does not guarantee feasible walking. ScaleBFM runs at 50 Hz, PD at 250 Hz.

`four_point_translate` uses world XYZ metres. `four_point_rotate` uses a world
axis-angle vector in radians and a pivot; rotation moves offset grasp points.
`image_pixel_to_world_plane` intersects a pixel ray with the explicitly supplied
workspace plane, not object depth. `four_point_place_local_point` converts an
explicit wrist-local offset to a wrist goal. Geometry tools do not execute.

DEX3 `grippers.left/right` are closure fractions: 0=open, 1=closed. Closure
ramps over the waypoint duration. Empty active lists allow a gripper-only
phase; its completion is not contact evidence. Preserve the intended closure
during lifting. Do not output q29, torques or whole-task open-loop scripts.

## Learn between attempts

When the episode finishes, read its native outcome and actual trajectory.
Summarize verified progress, failure evidence, rejected hypotheses and the
next discriminating attempt. Use `skill_update` to submit the complete revised
SKILL.md, a concise lesson and exact evidence paths. Retain useful findings,
remove disproven assumptions and avoid memorizing absolute object coordinates.
Respect the reported length cap. The host archives every accepted version;
invalid edits execute nothing and can be corrected.

The host starts another independent episode with the revised skill. Ten native
physical grasp successes across independent resets unlock SIMPLE transfer;
replays and repeated frames of one grasp never increase this count. Episode
failure is not campaign completion. Physics/transport faults end that attempt
without replaying uncertain actions; preserve evidence for the next attempt.
Use concise public explanations, never private chain-of-thought.
