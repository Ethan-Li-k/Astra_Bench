---
name: loco-manip-direct
description: Apply G1 visual control using task-local evidence and the current UMI-4 contract.
---

## Start and select

Read workspace.json, task_specification, this skill and experience_read. Current task and observed contract govern completion, limits and allowed sources. Use the exact interpreter; install nothing. No hidden object/contact state, evaluator access, demonstrations, other simulators or hardware. Record current problem, overall goal and errors to avoid in public notes.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions; reselect when the failure mode changes. Retrieve relevant versions and cited public evidence selectively. Earlier success never replaces the current objective or independent audit.

## Act and verify

Use the latest observation and unique request ID. State observed evidence, purpose and expected change. Supply all four wrist/ankle absolute world poses in metres and unit wxyz; declare active position/orientation. Inactive components follow the current contract. Never command joints or torques. Grippers ramp 0=open to1=closed, not measured force/aperture. Wrist origins and mesh bounds are not calibrated grasp centres or contacts.

Use one waypoint unless continuous chunks are explicitly enabled; obey current knot, duration, translation and rotation limits. Inspect fresh RGB and measured poses after every action, including public intermediate traces when needed. Separate request, tracking, contact hypothesis and task progress. Monitor both wrists and whole-body posture. Reanchor only with evidence; change a justified variable after failure.

Use render_intrinsics, pixel centres and current camera poses. Check robot reprojection and consistent stereo features; reject shadows, occlusion and uniform patches. Contour correspondence can change depth by centimetres. Ray-plane projection is not depth. Check full-hand clearance with uncertainty.

For supplied H001004 side grasps, remain open until the apple reaches the opposing hand plane inside the enclosure. Partial closure cannot replace unresolved enclosure. A different grasp needs its own geometry. Episode2's free-space preshape/top approach did not establish enclosure or pickup; it is not a successful workaround. Verify a short lift and independent retention; wrist ascent and overlap do not prove pickup. Human-feedback-assisted runs remain separate from autonomous Direct.

## XMovePick evidence

Episode1 ended in native_failure during its symmetric elevated-ankle/lowered-wrist test. Do not reuse it as a crouch primitive; exact failure cause is unobserved.

Episode2 ended at episode_step_budget after49 actions, with native_outcome=in_progress and no retained grasp/lift. Alternating and lateral support references sometimes advanced feet but also caused backward settling, yaw and lateral drift. Actions29/42 and43-46 are conditional approach evidence, not a validated gait. Grounded-foot/raised-hand recovery sometimes raised the head; it did not guarantee stability.

Raised stationary reach tracked better than forward-descent. Repeated descent degraded wrist attitude. Isolated rotation allowed position drift. Do not accumulate unachieved flattening requests. Severe inactive-hand attitude drift persisted. Tucking the left arm in action37 preceded large backward whole-body motion continuing through38; forward references in39 arrested it. The cause is unresolved; do not reuse that tuck as recovery.

Apple8 supplies conditional enclosure/retention evidence; door18 supplies unloaded recovery candidates. Their coordinates, heights and closure schedules do not transfer. Cube capsules do not describe mesh fingers.

Await complete responses; reasoning pauses physics. Timeout or finish_attempt stall is not termination: test a changed hypothesis using the returned observation. Stop physical actions at rollout_finished, preserve failures and sources, then submit evidence-backed skill_update within combined runtime caps. Shared promotion requires supervisor validation.
