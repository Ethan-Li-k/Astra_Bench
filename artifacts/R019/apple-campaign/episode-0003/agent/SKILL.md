---
name: loco-manip-direct
description: Learn visual apple placement using task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Pick up the apple beside the bowl, carry it above the opening, release inside and verify retention after hand withdrawal while standing. Preserve native SIMPLE outcome separately: accumulated apple-bowl contact does not prove placement inside.

Use registered physics services and loco_start exactly once. No demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets, other simulators or hardware. Read only listed campaign self-experience and robot geometry. Use the exact workspace interpreter; install nothing. Store artifacts only in designated RSI paths.

## Retrieve and select

Selectively read relevant experience and cited public trajectories. Before acting call experience_select with source IDs, applicability, adaptation and rejected details; reselect when failure mode changes. Grasp437/438 transfer retrieve-test-observe-correct, gradual closure and independent lift verification, not apple coordinates, dimensions, table height, closure or grasp attitude. Preserve decisions and uncertainties in public reasons.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joint names, fingers and closure. Use one reviewed waypoint, latest observation path and unique request ID. State evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. After every action inspect RGB and actual poses. Separate requested target, tracking, contact hypothesis and progress.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect 0.03m translation, 0.10rad rotation and 0.5-3s duration limits. Never output q29 or torques. Map joints by name. Grippers are ramped fractions: zero open, one closed.

Geometry tools calculate; scalebfm_act executes. Wrist frames are not calibrated TCPs. Check the whole hand using current named geometry and finger state, including opening, closure and rotation sweeps. Distal mesh bounds are not contact surfaces. Quaternion targets track only with orientation active. Preserve nonmoving references instead of accumulating measured bias; report position and attitude errors independently, including on timeout. Monitor actual ankles and body-camera response; arbitrary foot displacement is not verified walking.

## Visual manipulation

Use calibrated stereo correspondences with reprojection and uncertainty checks. Ray-plane projection is not depth. Reject shadows, clipped silhouette centres, featureless patches and inconsistent edges. Recompute camera geometry after body motion. Robot-point projections explain nonvisibility but do not replace visible manipulation evidence.

Acquire a visible, clear pregrasp before inward approach. Align opposing finger surfaces, close gradually and test a short lift. Verify apple motion relative to table in both views, then independently observe/hold. Closure, wrist motion, target_reached and overlapping pixels prove neither grasp nor placement. After slip, reopen with clearance and relocalize. Carry only a verified grasp above the rim, lower toward the visible opening, release, withdraw and inspect retention/support unless terminated.

## Task-specific evidence

Episode0001: 15 actions ended in policy_declared_stall, native in_progress, no grasp. Hands stayed invisible; cumulative elevation did not establish whole-hand clearance. Combined rise/rotation caused tracking failures and ankle drift. Retreat then ascent recovered elevation, so no absolute reach limit was established. Rough bowl stereo coordinates were unreliable; never preserve them as scene facts.

Episode0002: 19 actions ended in policy_declared_stall, native in_progress, no closure or grasp. Early20mm forward reach with active measured attitude reached within3mm/.011rad; isolated pitch reached within5mm/.024rad. Both hands still stayed invisible. Side reach increasingly undertracked despite accurate attitude: action14 gained9mm for25mm, residual20mm/.015rad. Later yaw reduced thumb inward projection, but action19 gained only1.6mm outward with19mm/.0014rad residuals. Index/middle outboard bounds did not clear the inward thumb or wrist. Ankles remained about1.2mm from references. Accurate yaw and target_reached never established a usable route.

Next hypothesis, unvalidated: shape the open-hand attitude at low fixed position before extending sideways. Test isolated yaw/roll and only a stereo/sweep-supported diagonal outward/up probe. Consider rear clearance only after visibly localizing the near edge. Do not replay cumulative ascent or saturated fixed-height lateral targets.

## Termination and learning

Stop physical actions immediately on rollout_finished. After at least three actions, finish_attempt may document an evidenced stall and changed hypothesis; it is not success. Do not fill the budget with idle holds. Separate local construction errors, explicit service errors and uncertain transport; never blindly retry an uncertain action.

After termination submit complete skill_update, concise lesson/change_summary and existing public rollout evidence from this episode. Check every length cap and retain versions. Keep task-specific rules separate from shared_candidate proposals; promote only after cross-task validation and grasp regression. Keep learning separate from frozen evaluation.
