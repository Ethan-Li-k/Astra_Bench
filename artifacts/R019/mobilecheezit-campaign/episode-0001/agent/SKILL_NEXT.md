---
name: loco-manip-direct
description: Use public visual evidence for mobile box pickup, transport and placement.
---

## Contract and sources

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, this skill and experience_read. Current task/interface overrides history. Use workspace Python; install nothing. Only RGB, calibration, named robot state/geometry and listed self-experience are allowed. No demonstrations, privileged object/contact state, evaluator/runtime inspection, other simulators or hardware.

Call loco_start once. Inspect stereo, calibration, measured/reference poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions; reselect when failures change. Record current problem, goal, prohibited repeats and next test in notes. Sources: shared437/438 retrieval, measured-box1 enclosure/hold, boxplace4 retention/release, door19 conditional recovery. Coordinates and gait do not transfer.

## Execute and verify

Use latest observation and unique request ID. State evidence, purpose and expected change. Supply all four named wrist/ankle world positions in metres and unit wxyz quaternions; declare active position/orientation. Inactive components follow current contract. Never output joints or torques. Closure0–1 is a command, not force/aperture; wrist frames are not calibrated TCPs.

Use one waypoint unless continuous chunks are enabled. Respect segment/cumulative translation, rotation, duration and common-active/gripper bounds. Future knots do not await arrival. After every chunk inspect fresh RGB, measured poses and relevant motion traces. Separate requested motion, tracking, contact hypothesis and task progress. Change a justified variable after failure.

Use render_intrinsics and pixel centres. Ray-plane projection is not depth. Reject occluded/inconsistent stereo corners and shadows; reproject and relocalize after movement. Inspect palm, proximal and distal mesh clearance through approach/closure. Hull bounds reject interference but do not prove contact. Require visible opposing enclosure before closure, then a short lift and separate original-target hold. Overlap, wrist ascent and target_reached do not prove retention.

## Mobile Cheez-It episode0001: task-specific evidence

SIMPLE/MuJoCo, not Isaac. Budget ended after65 actions/240.02 controlled seconds; native_outcome remained in_progress. Endpoint standing; box flat on first table. Destination, completed carrying and placement unverified.

Retrieve public013–029 selectively. Inward013 tracked position but changed wrist attitude0.83rad. Recheck achieved axes after translation; do not preserve a mistaken attitude anchor. Early0.20 closure/lift failed. Revised lower enclosure and0.40 closure produced lift025, independent hold026 and larger retained lift027. Revalidate fractions/poses.

Loaded bilateral yaw028 retained box but caused rearward support drift and tilt. Withdrawal029 changed attitude and lost box onto first table. Do not reuse this as payload gait. Locate destination and test the unloaded route before the next pickup; loaded motion still needs small independent retention tests.

Recovery042 ankle-pitch correction coincided with large retreat; lowering/forward references did not arrest it. Neutralward wrist correction045 coincided with recovery; causality is provisional. Unloaded046/047 advanced supports, then arcs stalled. Pre-shift plus separate swing054/055 advanced individual feet;062 gained lateral motion but063 did not mirror it. Requested ankle height is not clearance or validated gait.

## Continue and revise

Await complete responses; simulation pauses during reasoning. finish_attempt records a changed hypothesis, never termination. Continue useful tests until rollout_finished, then stop physics. Avoid idle budget filling. Submit complete skill_update with concise lesson, change_summary and public evidence; preserve failures, versions and source selection. Host owns recording/export. Respect combined length caps. Keep this task_specific; shared promotion requires cross-task validation and grasp regression.
