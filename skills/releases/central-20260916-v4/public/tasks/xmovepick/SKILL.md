---
name: loco-manip-direct
description: Apply G1 visual control using task-local evidence and the current UMI-4 contract.
---

## Start and select

Read workspace.json, task_specification, this skill and experience_read. No hidden object/contact state, evaluator access, demonstrations, other simulators or hardware. Record current problem, overall goal and errors to avoid in public notes.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions; reselect when failure mode changes. Retrieve relevant versions and cited public evidence selectively. Native success never replaces independent task audit.

## Act and verify

Use the latest observation and unique request ID. State evidence, purpose and expected change. Supply all four wrist/ankle absolute world poses in metres and unit wxyz; declare active position/orientation. Inactive components follow the current contract. Never command joints or torques. Grippers ramp 0=open to1=closed, not measured force/aperture. Wrist origins and mesh bounds are not calibrated grasp centres or contacts.

Use one waypoint unless continuous chunks are explicitly enabled; obey current knot, duration, translation and rotation limits. Inspect fresh RGB and measured poses after every action, including relevant traces. Separate request, tracking, contact hypothesis and task progress. Monitor both wrists, pelvis height/tilt and support drift. Reanchor only with evidence; change a justified variable after failure.

Use render_intrinsics, pixel centres and current camera poses. Check robot reprojection and consistent stereo features; reject shadows, occlusion and uniform patches. Contour correspondence can change depth by centimetres. Ray-plane projection is not depth. Check full-hand clearance with uncertainty; visible surface estimates are not object centres.

For supplied H001004 side grasps, remain open until the apple reaches opposing hand surfaces inside the enclosure. Partial closure cannot replace unresolved enclosure. Inclined or top approaches need their own geometry and table-clearance checks. Verify short-lift co-motion and separate retention before further lift; wrist ascent and overlap alone do not prove pickup. Human-feedback-assisted runs remain separate from autonomous Direct.

## XMovePick entry

Retrieve observations25-31: open inclined enclosure, closure, short lift, separate hold and continued retained lift. Adapt geometry; do not replay poses or closure. Final stance was upright; loaded walking is untested.

Actions1-7 advanced feet but retained support retreat, yaw and a failed catch-up: not a validated gait. Descent steepened wrist pitch; orientation-only flattening partly tracked with upward drift. Thumb-down rotation improved opposing geometry, yet low distal clearance blocked descent. Coordinated lateral wrists partly overcame inward saturation.

The unilateral elevated-left reference in21-28 did not lift that ankle and accompanied progressive pelvis lowering. Grounded references plus raised wrists in29 restored height during the short lift. Do not call this a crouch primitive or assume stability from low tilt alone.

Preserve episode1 bilateral elevated-ankle/lowered-wrist native failure, episode2 budget end without retained pickup, failed left-tuck recovery and unvalidated top-preshape. Apple8 supplies enclosure/retention candidates; door18 supplies unloaded recovery candidates. Their coordinates and heights do not transfer; cube capsules do not describe mesh fingers.

Await complete responses; reasoning pauses physics. Timeout or finish_attempt stall is not termination: test the changed hypothesis in the same episode. Stop at rollout_finished, preserve failures and sources, then submit evidence-backed skill_update within combined runtime caps. Only central publication changes loaded skills; skill_update saves a proposal.
