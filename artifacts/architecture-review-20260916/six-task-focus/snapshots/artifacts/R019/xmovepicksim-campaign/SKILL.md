---
name: loco-manip-direct
description: Approach and grasp the measured-table cracker box using public evidence.
---

## Contract and selection

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, SKILL.md and experience_read. Use workspace Python; install nothing. Only listed self-experience, RGB, calibration, named robot state and geometry are allowed. No demonstrations, object/contact truth, evaluator/runtime inspection, other simulators or hardware. Act through registered services.

Call loco_start once. Inspect stereo, calibration, measured/reference poses, joints and closure. Before acting, experience_select records sources, applicability, adaptations and exclusions; reselect on changed failures. Note problem, goal, errors and next test. Shared437/438 supply retrieval; bendpick6 opposition; door19 unloading. Coordinates and gait do not transfer.

## Execute and observe

Use latest observation and unique request ID. State evidence, purpose and expected change. Include all four named wrist/ankle absolute world positions in metres and unit wxyz quaternions. Declare active.position/orientation; inactive components follow current contract. Never output joints or torques. Closure0–1 is commanded fraction, not aperture/force. Wrist frames are not calibrated TCPs.

Use one waypoint unless continuous chunks are enabled. Respect current segment, cumulative, duration and rotation bounds; future knots do not wait for arrival. Inspect fresh RGB and actual poses after each action, using motion traces when needed. Separate tracking, contact and progress. Change a justified variable after failure.

Use render_intrinsics and pixel centres. Projection is not depth. Reject occluded/inconsistent stereo or shadows; reproject fits and relocalize after movement. Hull checks can reject interference, not prove contact. Check palm, proximal and distal links through motion/closure; reject old capsule geometry.

## Task-specific episode0001

SIMPLE/MuJoCo, not Isaac. Native success at038 after38 actions/135.54 physical seconds. Visible upward box-hand co-motion persisted through a separate hold before final lift; endpoint support is visible. No post-threshold dwell or stereo height certification; host audit is separate.

Approach002/003/006/008/019 moved supports;001/004/007/020/021 undertracked. Raised ankle arcs with lateral open-hand bias sometimes advanced supports. Withdrawal/lowering restored progress019 after elevated reach stalled. Ankles advanced0.388/0.232m with drift; no generic/loaded gait established.

Pitch/yaw undertracked despite wrist position tracking. Orientation-only013 drifted medially45mm. Do not force bendpick's steep attitude. Closer stance, shallower achieved attitude and current mesh checks enabled entry. Hold the other wrist to limit drift.

Retrieve023–038 selectively. Free-space0.25 closure characterized geometry, not acquisition. Curled fingers and yaw drift rejected deep entry;027 reopened.028 enclosed upper box with thumb ahead of front, fingers beyond rear and palm above top. 

029/030 closed0.15/0.25. Probe031 plus hold032 raised wrist without convincing box rise.033 changed closure to0.35.034/035 showed coupling with tilt; early corner fits stayed ambiguous.036 plus independent1.5s hold037 showed retained upward co-motion.038 requested20mm more and reached native success. Revalidate each reset.

## Continue and revise

Closure, overlap, shadows, wrist ascent and target_reached do not prove grasp. Require short lift and separate original-target hold; distinguish tilt from lift. Reopen safely and change geometry after loss.

Await complete responses; reasoning pauses simulation. Continue useful safe tests until rollout_finished, then stop physics. finish_attempt records a stall and changed hypothesis, never termination or success. Avoid idle budget filling.

After termination submit complete skill_update with lesson, change_summary and public evidence. Preserve failures/versions; host owns recording/export. Respect combined caps. Use task_specific; shared promotion needs cross-task validation and grasp regression.
