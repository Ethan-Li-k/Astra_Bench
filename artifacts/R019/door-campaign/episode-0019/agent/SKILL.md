---
name: loco-manip-direct
description: Apply G1 UMI-4 visual control with task-local public experience; revalidate when task, controller or geometry changes.
---

## Start and select

Read workspace.json, task_specification, this skill and experience_read. The task and current observed contract govern completion, controller limits and allowed sources. Record 当前问题 / 总目标 / 不可重犯的错误 before decisions; keep concise public observations, hypotheses and next tests in notes.

Call loco_start once. Inspect RGB, calibration, named measured/reference robot poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions. Reselect when evidence changes the failure mode. Retrieve relevant task versions and cited public trajectories; do not import a whole archive. A native-success memory label is not independent task validation.

## Execute and observe

Use the latest observation and unique request ID. State visible evidence, purpose and expected change in reason. Supply all four named wrist/ankle poses in world metres and unit wxyz; declare active.position/orientation. Inactive components follow the current contract. Never output joints or torques. Grippers ramp 0=open, 1=closed; closure is not measured force or aperture. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

Use reported single-waypoint bounds; multiple knots require the enabled continuous contract. After each action inspect fresh RGB and measured motion, including intermediate public robot traces when endpoint return hides motion. Ankle motion does not establish sole clearance, stable gait or approach completion. Tracking timeout is distinct from task failure. Reanchor only with evidence; change a justified variable after a failed hypothesis.

Use delivered render_intrinsics and pixel centers; revalidate old fovy-only estimates. Ray-plane projection is not depth. Reject inconsistent stereo matches, shadows and occlusion. Check whole-hand clearance after posture changes. For grasping, establish a visible opposing enclosure before closure, then test a short lift and separate observable hold. Commanded closure, pixel overlap and wrist motion do not establish retention. Apply human semantic rules only when explicitly supplied in this task; preserve their provenance and scope.

## Conditional experience

Table-cube437/438 support retrieve-adapt-observe; their coordinates, closure and capsule geometry do not transfer automatically to SIMPLE mesh fingers. For door pushing, retrieve this campaign's public versions: low-arm approach, support adjustment and unloaded recovery are candidates, not a proven gait. Stop at rollout_finished even when tracking reports timeout. Do not substitute handle pulling for panel pushing.

For container placement, verify retained lift, clearance of object and fingers over the rim, transport, release and stable placement; native contact alone is insufficient. For faucet contact, first establish visible moving-part identity and a testable coupling hypothesis; repeated occluded closure supplies little new evidence. For floor pickup, establish a reachable stationary grasp before lifting and transport; diagnostic movement is not full task success.

After terminal execution, preserve failures, sources and prior versions. Revise this short entrypoint; keep numerical task procedures in versioned public experience. Respect combined skill-plus-runtime caps reported by experience_read. Shared publication belongs to the supervisor after matching-contract validation and regression.

## Current task entry

Retrieve the latest completed version and selected cited actions. Revalidate low-arm approach, support drift and whole-hand clearance. After forward reach saturation, withdraw/lower the open hand, adjust unloaded stance, then re-raise. If catch-up stalls, reassess foot stagger and lateral coordination; neither wrist shift nor ankle rise proves unloading. Separate lateral tracking error from forward saturation. These are task-local candidates, not a proven gait. Continue until host termination.
