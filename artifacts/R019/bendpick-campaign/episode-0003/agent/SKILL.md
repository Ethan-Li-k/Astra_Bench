---
name: loco-manip-direct
description: Learn native SIMPLE cracker-box grasping from public visual evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Locate the cracker box by visible geometry, grasp with a Dex3 hand, and lift at least 8 cm above its initial height while standing. Require one independently reset native success. Native height success alone does not establish retention; independently assess box-hand co-motion and visible support. Preserve this objective over prior cube tasks.

Read workspace.json, detailed task_specification, assembled SKILL.md and experience_read. Use the exact workspace Python; install nothing. Only listed self-experience, cited public rollout evidence, RGB, named robot state, camera calibration and robot geometry are allowed. No demonstrations, hidden object/contact state, evaluator/runtime inspection, other simulators or hardware. All physical actions use registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints, closure commands and native distal mesh bounds. Before acting, experience_select records source IDs, applicability, adaptations and rejected transfers. Re-select when failure mode changes. Retrieve relevant versions selectively. Shared grasp episodes437/438 support retrieve-test-observe-correct, gradual closure, probes and independent holds; their coordinates, capsules, planes, attitudes and closure values require fresh validation.

Use one reviewed waypoint, latest observation path/ID and unique request ID. In reason state observed evidence, purpose and expected observable change. After every completed action inspect fresh RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress. Preserve decisions, errors, uncertainty and next hypothesis in public records. Never blindly replay, repeat unchanged failures or accumulate biased measured anchors.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect 0.03 m translation, 0.10 rad rotation and 0.5–3 s duration limits. Keep feet supported. Never output q29 or torques. Closure fractions 0–1 are commands, not aperture or force. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

## Geometry and verification

Identify the white rectangular target separately from rounded distractors. Ray-plane projection is not depth. Use calibrated stereo correspondence, rejecting shadows, occlusions and inconsistent reprojections. Cuboid fits must match both views; dimensions remain estimates. Re-localize after contact, including table-edge margin. During entry, compare calibrated landmarks before calling the box stationary; coarse views missed displacement in episode0002.

Use current native distal mesh bounds and link origins, not cube capsules. Bounds are conservative ranges, not contact surfaces. A thumb-bound minimum below the top does not establish useful contact depth. Check whole-hand clearance through rotation, approach and closure; recompute using achieved attitude.

Review thumb versus index/middle opposition before contact closure. Free-space closure can characterize geometry but is not a validated preclosure recipe. Test a 10–20 mm lift and one independent original-target hold. Wrist ascent, closure, target_reached and pixel overlap do not prove grasp. Require box-hand co-motion and visible support before completing the lift. After loss, reopen with clearance and reassess.

## Task-specific failures

Episode0001: 32 actions, no success. Isolated rotations helped at one anchor but not at forward/inward reach. Descents undertracked despite opening or orientation changes. Closures .30/.40 tipped the box; probe/hold were ambiguous, then wrist ascent with box settling rejected retention. Withdrawal left the box flat near the front edge. Its fitted top .619 m and dimensions are reset-specific estimates.

Episode0002: 44 actions on SimpleLiveSim, no native success or verified retention. Lateral rotations002–015 tracked well. Side-clear descent016 achieved21.8 mm of25 mm but developed .106 rad attitude error; correction017 failed. Forward descent020 stalled; orientation-free021 and coordinated lowering025 did not recover it. These controls strengthen a pose-dependent tracking hypothesis without proving its cause.

Free-space closures026/027 at .15/.25 characterized native bounds. Forward side-entry later displaced/possibly tilted the box; conservative bounds and coarse views overstated clearance. Probe039 raised wrist13.2 mm; hold040 added2 mm while stereo landmarks showed settling and a lower corner near table height. Open withdrawal041–044 cleared the hand; feet remained supported. Both episodes ended through finish_attempt, not success.

Next hypothesis, unverified: change hand or grasp attitude and validate a low side-clear pose before entry, with clearly deeper thumb opposition and visible near/far-face clearance. Check calibrated landmarks earlier. Do not reuse failed coordinates or .20/.25 preclosure as recipes.

## Termination and learning

Await complete service responses; reasoning pauses simulation. Stop physical actions on rollout_finished. After at least three actions, finish_attempt may end an evidenced stall with a changed hypothesis; never count it as success or fill budget with idle holds.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence paths within all caps. Keep these corrections task_specific. Shared proposals require cross-task validation and grasp regression; local revisions never overwrite shared core.
