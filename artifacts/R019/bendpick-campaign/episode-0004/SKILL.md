---
name: loco-manip-direct
description: Learn native SIMPLE cracker-box grasping from public visual evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Identify the cracker box by visible geometry, grasp with a Dex3 hand, and lift at least 8 cm above its initial height while standing. Require one independently reset native success. Native height success alone does not establish retention; assess box-hand co-motion and visible support separately.

Read workspace.json, detailed task_specification, assembled SKILL.md and experience_read. Use the exact workspace Python; install nothing. Only listed self-experience, cited public rollout evidence, RGB, named robot state, camera calibration and robot geometry are allowed. No demonstrations, hidden object/contact state, evaluator/runtime inspection, other simulators or hardware. All physical actions use registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints, closure commands and native distal mesh bounds. Before acting, experience_select records source IDs, applicability, adaptations and rejected transfers. Re-select when failure mode changes; retrieve relevant versions selectively. Shared episodes437/438 support retrieve-test-observe-correct, gradual closure, probes and independent holds. Their coordinates, capsules, planes, attitudes and closure values require fresh validation.

Use one reviewed waypoint, latest observation path/ID and unique request ID. State observed evidence, purpose and expected change in reason. After every action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Record errors, uncertainty and next hypothesis. Never blindly replay, repeat unchanged failures or accumulate biased measured anchors.

Include all four absolute positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect 0.03 m translation, 0.10 rad rotation and 0.5–3 s duration limits. Keep feet supported; inspect accumulated drift. Never output q29 or torques. Closure fractions are commands, not aperture or force. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

## Geometry and verification

Distinguish the white rectangular target from rounded distractors. Ray-plane projection is not depth. Use calibrated stereo correspondence, rejecting shadows, occlusions and inconsistent reprojections. Cuboid fits must match both views; dimensions remain estimates.

During entry compare visible landmarks against calibrated reprojections before calling the box stationary. Occluded corners are uninformative. Pixel displacement can indicate translation or tilt; re-localize after settling and check table-edge margin.

Use current native distal bounds and link origins, not cube capsules. Bounds are conservative ranges, not contact surfaces. A thumb-bound minimum below the top does not establish useful contact depth. Distal clearance does not certify palm/proximal clearance. Review whole-hand geometry through rotation, entry and closure using achieved attitude. An illustrative wrist-local point is not a palm surface or TCP.

Validate attitude across medial reach, not only at the side anchor. Orientation-only controls can improve angular tracking while allowing positional drift; inspect actual position before reactivating it. Increased approach height may improve clearance while leaving thumb opposition too shallow.

Review thumb versus index/middle opposition before contact closure. Free-space closure characterizes geometry, not a preclosure recipe. Test a 10–20 mm lift and one independent original-target hold. Wrist ascent, closure, target_reached and overlap do not prove grasp. Require box-hand co-motion and visible support before further lift. After loss, reopen with clearance.

## Task-specific evidence

Episodes0001/0002 ended through finish_attempt without native success or verified retention. Episode0001 descents undertracked and .30/.40 closures tipped the box. Episode0002 lateral rotations tracked, but low/forward descent and orientation-free/coordinated controls did not recover the desired pose. Entry displaced the box; probe/hold showed settling. Their coordinates and closures are not recipes.

Episode0003:52 actions on SimpleLiveSim, no success. Left-hand rolled descent014/015 lowered about47 mm but developed attitude errors. Low entry033 moved/tilted the box despite conservative distal checks; withdrawal allowed settling near its initial outline. Higher orientation-only controls improved pitch with drift. High entry042–045 improved clearance, but medial yaw bias and shallow thumb opposition persisted. Closure048 at .30 tipped the box. Probe049 raised wrist5.5 mm; original-target hold050 added10.9 mm while the box rotated/fell toward the front edge. Retention was rejected. Open withdrawal051/052 separated the hand; feet remained supported.

Next hypothesis, unverified: establish flatter pitch and yaw compatible with medial reach before entry, then demonstrate deeper thumb-side opposition and palm clearance across the closure trajectory. If achieved attitude cannot preserve opposition, change approach axis instead of chasing orientation or closing harder. No successful box-grasp recipe exists yet.

## Termination and learning

Await complete responses; reasoning pauses simulation. Stop physical actions on rollout_finished. After at least three actions, finish_attempt may end an evidenced stall with a changed hypothesis; never count it as success or fill budget with idle holds.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence paths within all caps. Keep corrections task_specific. Shared proposals need cross-task validation and grasp regression; local revisions never overwrite shared core. Preserve prior versions and failures; host owns recording/export.
