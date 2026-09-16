---
name: loco-manip-direct
description: Learn G1 SIMPLE manipulation through visual four-point control and recorded self-experience.
---

# SIMPLE Direct skill

Use gpt-6-astra/xhigh. Learn through registered physics services and revise this
skill from your actual attempts. No human demonstrations, pretrained task
trajectories, separate model API, runtime edits or real hardware.

## Task and evidence

Read workspace.json and experience_read. The workspace task is the complete
objective for this episode. For door pushing, push the initially closed door
open at least 30 degrees from its initial position and keep it open for at
least one second while standing. Hand contact must cause the opening.
The campaign requires ten independent door successes. Other available SIMPLE
manipulation tasks each require at least one independent success.

Read only your public observations, receipts, current skill and experience.
Robot state and camera calibration are available. Object pose, joint angle,
contact truth, host recordings, evaluation internals and other experiment
directories are not actor inputs. Infer object motion from RGB. No fixed
table height, object size or grasp pose is supplied for this task.
Use the exact Python interpreter in workspace.json. Install nothing.

## Observe and act

1. Start once with loco_start and its supplied output directory. Inspect every
   available head view and measured/reference robot poses. Identify the target,
   its moving part, accessible contact surface and free space from images.
2. State what is measured, what is uncertain and what the next bounded action
   tests. Use the latest observation and unique request IDs. Follow next_call.
3. Send one waypoint with scalebfm_act; inspect the complete returned receipt
   and images before another action. Model reasoning has no ten-second cutoff.
   Simulation currently pauses during reasoning; this is not a real-time test.
4. Separate tracking error from task progress. A timed-out wrist command may
   still have moved the object. Compare actual position, attitude and images.
   Never resend an action whose execution is uncertain; read its receipt first.
5. For pushing, establish gentle contact and test a small displacement. Check
   that the door rotates relative to the frame, then continue bounded progress.
   A moving wrist or occluded handle is not proof. Infer hinge direction from
   visual response. Reposition if contact slips; do not repeat unchanged force.
6. Continue until rollout_finished, including after tracking timeouts. Verify
   the full goal and dwell, distinguishing a latched native success from the
   final visible state. On budget exhaustion, preserve the failed trajectory.

## Four-point interface

All poses are absolute world position_world_m and unit quaternion_wxyz.
The four names are left_wrist_yaw_link, right_wrist_yaw_link,
left_ankle_roll_link and right_ankle_roll_link. Declare active.position and
active.orientation; inactive components preserve reference. Joint arrays
are mapped by name. Never output torques, q29 arrays or open-loop task scripts.

Each waypoint is within 0.03 m and 0.10 rad of current measurement and lasts
0.5-3 s. Reobserve after one waypoint. Tracker runs at 50 Hz; SIMPLE physics
and native PD run at 200 Hz. Feet define support; arbitrary foot motion does
not establish feasible walking. Wrist links are not calibrated hand TCPs.

Grippers.left/right are closure fractions 0=open, 1=closed. Existing grasp
experience shows stronger closure alone did not reliably improve retention;
do not import its object-specific closure or grasp coordinates as an answer.
Explicit position holds and comparison with contact-time attitude help
diagnose drift; fixed attitude alone did not guarantee retention.

four_point_translate uses world metres; four_point_rotate uses world
axis-angle radians and a pivot. four_point_place_local_point needs a verified
wrist-local offset. Geometry tools calculate without executing. Ray-plane
projection requires a justified plane and is not a generic depth sensor.

## Learn and preserve

Record exact failures by layer: local script parse, service rejection,
tracking timeout, visual contact loss or goal failure. Do not invent causes.
After terminal evidence, submit complete revised markdown and one concise
lesson via skill_update with this episode's public evidence paths. Preserve
frontmatter and check 831 words / 6250 characters / 5357 non-whitespace caps.
Then return; the host schedules the next independent task episode.
