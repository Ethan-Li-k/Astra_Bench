---
name: loco-manip-direct
description: Apply G1 UMI-4 visual control using task-local evidence; revalidate controller, geometry and completion.
---

## Start and select

Read workspace.json, task_specification, this skill and experience_read. Current task and observed interface govern allowed sources, limits and completion. Record 当前问题 / 总目标 / 不可重犯的错误 before decisions; preserve observations, hypotheses and next tests in public notes or action reasons.

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions. Reselect when failure mode changes. Retrieve relevant versions and cited public trajectories selectively. Native-success labels are not independent task validation.

## Execute and observe

Use the latest observation and unique request ID. Explain visible evidence, purpose and expected change. Supply all four named wrist/ankle poses in world metres with unit wxyz; declare active position/orientation. Inactive components follow the current contract. Never command joints or torques. Closure ramps from 0=open to 1=closed; it is not force or aperture. Wrist origins and robot mesh bounds are not calibrated grasp centres or contacts.

Obey current waypoint bounds; multiple knots require an explicitly enabled continuous contract. Inspect fresh RGB and measured motion after every action, including public intermediate traces when needed. Distinguish tracking timeout from task failure. Reanchor only with evidence. Position-only tracking can preserve references while allowing attitude error; monitor actual whole-hand clearance and retention.

Use delivered render_intrinsics, pixel-centre convention and current camera poses. Check robot reprojection before trusting depth. Reject inconsistent stereo correspondences, uniform patches, shadows and occlusion. Ray-plane projection is not depth. Older empirical fits and fovy-only estimates require revalidation.

Establish visible opposing enclosure before closure, then verify short lift and separate observable hold. Finger deviations, overlap and wrist motion alone do not establish retention. Before transport check object and fingers clear the rim. Verify release, withdrawal and stable placement when execution permits. Stop immediately at rollout_finished; preserve missing verification explicitly. A stall changes the next test, not episode termination.

## Apple entry

Apply supplied H001004 only to this side-grasp task: remain open until the apple reaches the hand plane inside the palm enclosure. Do not probe closure to resolve missing enclosure.

Retrieve episode-0008 observations 0100–0117 and its lesson. A lower, rearward open approach preceded retained lift, transport and native success; the earlier higher grasp failed. Use those poses as adaptation candidates, not a replay. Final RGB shows release inside the bowl, but native termination prevented withdrawal and later stability verification. This was human-feedback-assisted, without demonstration.

Preserve version7 failures, all episode evidence and prior versions. Cube coordinates/capsules do not transfer to mesh fingers. Ankle displacement is not gait or sole clearance. After terminal execution submit skill_update within combined runtime caps; detailed numbers belong in versioned experience. Shared publication requires supervisor validation.
