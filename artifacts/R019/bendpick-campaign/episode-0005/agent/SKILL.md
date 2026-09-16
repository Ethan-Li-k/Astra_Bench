---
name: loco-manip-direct
description: Learn native SIMPLE cracker-box grasping from public visual evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Identify the cracker box by visible geometry, grasp with a Dex3 hand, and lift it at least8cm above its initial height while standing. Require one independently reset native success. Native height success alone does not establish retention; assess box-hand co-motion and visible support separately.

Read workspace.json, detailed task_specification, assembled SKILL.md and experience_read. Use the exact workspace Python; install nothing. Only listed self-experience, cited public rollout evidence, RGB, named robot state, camera calibration and robot geometry are allowed. No demonstrations, hidden object/contact state, evaluator/runtime inspection, other simulators or hardware. All physical actions use registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints, closure commands and native distal bounds. Before acting, experience_select records source IDs, applicability, adaptations and rejected transfers. Re-select when failure mode changes; retrieve relevant versions selectively. Shared episodes437/438 support retrieve-test-observe-correct, gradual closure, probes and independent holds. Their coordinates, capsules, planes, attitudes and closure values require fresh validation.

Use one reviewed waypoint, latest observation path/ID and unique request ID. State observed evidence, purpose and expected change in reason. After every action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Record errors, uncertainty and next hypothesis. Never blindly replay, repeat unchanged failures or accumulate biased measured anchors.

Include all four absolute positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect0.03m translation,0.10rad rotation and0.5–3s duration limits. Keep feet supported; inspect accumulated drift. Never output q29 or torques. Closure fractions are commands, not aperture or force. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

## Geometry and verification

Distinguish the white rectangular target from rounded distractors. Ray-plane projection is not depth. Use calibrated stereo correspondence, rejecting shadows, occlusions and inconsistent reprojections. Fit visible edges carefully: small disparity errors can substantially bias height. Cuboid estimates must match both views.

During entry compare visible landmarks against calibrated reprojections before calling the box stationary. Occluded corners are uninformative. Pixel displacement can indicate translation or tilt; re-localize after settling and check table-edge margin.

Use current native distal bounds and link origins, not cube capsules. Bounds are conservative ranges, not contact surfaces. A thumb-bound minimum below the top does not establish useful contact depth. Distal clearance does not certify palm/proximal clearance. Review whole-hand geometry through rotation, entry and closure using achieved attitude.

Validate attitude across medial reach. Orientation-only controls can improve angular tracking while allowing positional drift; inspect position before reactivating it. Flatter pitch achieved high at the side may steepen during descent. Near-zero yaw alone does not establish safe enclosure.

Review thumb versus index/middle opposition before contact closure. Free-space closure characterizes geometry, not a preclosure recipe. Test a10–20mm lift and an independent original-target hold. Wrist ascent, closure, target_reached and overlap do not prove grasp. Require box-hand co-motion and visible support before further lift. After loss, reopen with clearance.

## Task-specific evidence

Episodes0001–0004 ended through finish_attempt without native success or verified retention. Current backend: SimpleLiveSim, not Isaac. Prior versions preserve detailed failures.

0001: descent undertracked; .30/.40 closures tipped the box.
0002: lateral rotation tracked, but low/forward and orientation-free/coordinated descent did not recover pose; entry displaced the box and probe/hold showed settling.
0003: rolled descent lowered47mm with attitude drift. Low entry displaced the box; high entry retained shallow thumb opposition and yaw bias. Closure.30 tipped it; probe/hold raised the wrist while the box fell.

0004:28 actions, about113.16s. Right orientation-only flattening improved tracking with drift; descent steepened pitch. Rolled approach reached roughly.719–.731m wrist height, but original lower targets undertracked. Position-only016 did not recover descent. Free-space.15/.25 closure characterized shallow opposition. Near-zero-yaw entry026 displaced visible corners despite distal clearance estimates. Open withdrawal027/028 separated the hand; no contact closure/lift was attempted. Feet stayed supported with about3mm horizontal drift.

Next hypothesis, unverified: change grasp axis using a yawed, more horizontal right-side approach. Establish low-pose tracking and deeper opposition before entry; validate palm/proximal clearance across the entire sweep. Do not repeat rolled forward entry or close harder. No successful box recipe exists.

## Termination and learning

Await complete responses; reasoning pauses simulation. Stop physical actions on rollout_finished. After at least three actions, finish_attempt may end an evidenced stall with a changed hypothesis; never count it as success or fill budget with idle holds.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence paths within all caps. Keep corrections task_specific. Shared proposals need cross-task validation and grasp regression; local revisions never overwrite shared core. Preserve prior versions and failures; host owns recording/export.
