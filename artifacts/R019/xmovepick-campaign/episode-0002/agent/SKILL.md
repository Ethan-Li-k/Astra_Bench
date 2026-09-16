---
name: loco-manip-direct
description: Apply G1 visual control using task-local evidence and the current UMI-4 contract.
---

## Start and select

Read workspace.json, task_specification, this skill and experience_read. Current task and observed contract govern completion, limits and allowed sources. Use the exact interpreter; install nothing. No hidden object/contact state, evaluator access, demonstrations, other simulators or hardware. Record current problem, overall goal and errors to avoid in public notes.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions; reselect when the failure mode changes. Retrieve relevant versions and cited public evidence selectively. Earlier success never replaces the current objective or independent audit.

## Act and verify

Use the latest observation and unique request ID. State observed evidence, purpose and expected change. Supply all four wrist/ankle absolute world poses in metres and unit wxyz; declare active position/orientation. Inactive components follow the current contract. Never command joints or torques. Grippers ramp 0=open to 1=closed, not measured force/aperture. Wrist origins and robot mesh bounds are not calibrated grasp centres or contacts.

Use one waypoint unless continuous chunks are explicitly enabled; obey current knot, duration, translation and rotation limits. Inspect fresh RGB and measured poses after every action, including intermediate public traces when needed. Separate target request, tracking, contact hypothesis and task progress. Monitor inactive-hand drift and whole-body posture as well as the active hand. Reanchor only with evidence; change a justified variable after failure.

Use render_intrinsics, pixel-centre convention and current camera poses. Check robot reprojection and consistent stereo features; reject shadows, occlusion and uniform patches. Ray-plane projection is not depth. Preserve pixel/depth uncertainty and check whole-hand clearance.

For this supplied H001004 side-grasp rule, remain open until the apple reaches the opposing hand plane inside the enclosure. Do not use partial closure to replace unresolved enclosure. After closing, test a short lift and independent retention observation; wrist ascent and pixel overlap do not prove pickup. This human-feedback-assisted run has no demonstration and is separate from autonomous Direct. The rule is not a universal top-grasp height requirement.

## XMovePick evidence

Episode0001 ended in native_failure during action28; no closure, grasp or lift occurred. Actions3-20 achieved partial alternating support advance, with backward settling and outward foot yaw. Small simultaneous forward references and a transient low foot arc did not move support. These are approach candidates, not a validated gait or loaded-walking skill.

Closer stance improved one wrist target, but forward/descent often degraded attitude. Raising the open hand improved pitch only partly. Diagnose reach, posture and full-finger clearance before further descent; do not accumulate flattening requests as if tracked. The symmetric elevated-ankle/lowered-wrist posture test terminated after 0.88s with feet still near the floor. Do not reuse it as a crouch primitive; the exact native failure cause is unobserved.

Apple8 supplies conditional enclosure/retention evidence; door18 supplies unloaded recovery candidates. Their coordinates, heights and closure schedules do not transfer. Cube capsules do not describe these mesh fingers.

Await complete inference and service responses; reasoning pauses physics. A tracking timeout or finish_attempt stall is not termination: follow the returned observation with a changed test. Stop physical actions at rollout_finished. Then preserve failures and sources and submit evidence-backed skill_update within combined runtime caps. Shared promotion requires supervisor validation and regression.
