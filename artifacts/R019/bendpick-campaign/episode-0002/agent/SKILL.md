---
name: loco-manip-direct
description: Learn native SIMPLE cracker-box grasping from public visual evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Locate the cracker box by visible geometry, grasp with a Dex3 hand, lift at least 8 cm above its initial height while standing. One independently reset native success is required. Native height success does not establish secure retention: independently assess box-hand co-motion and visible support. Preserve this objective over prior cube tasks.

Read workspace.json, detailed task_specification, assembled SKILL.md and experience_read. Use the exact workspace Python; install nothing. Only listed self-experience, cited public rollout evidence, RGB, named robot state, camera calibration and robot geometry are allowed. No demonstrations, hidden object/contact state, evaluator/runtime inspection, other simulators or hardware. All physical actions use registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints, commanded closure and native distal mesh bounds. Before acting, experience_select must record source IDs, applicability, adaptations and rejected transfers. Re-select when failure mode changes. Retrieve relevant versions/trajectories selectively. Shared grasp episodes437/438 support retrieve-test-observe-correct, gradual closure, lift probes and independent holds; their coordinates, capsule geometry, support plane, attitude and closure values require fresh validation.

Use one reviewed waypoint, latest observation path/ID and unique request ID. Explain observed evidence, purpose and expected observable change in reason. After every completed action inspect fresh RGB and actual poses. Separate target request, tracking, contact hypothesis and task progress. Preserve decisions, tool feedback, uncertainty and next hypothesis in public records/notes. Never blindly replay, repeat unchanged failures, or accumulate biased measured anchors.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect reported limits: 0.03 m translation,0.10 rad rotation,0.5–3 s duration. Keep feet supported. Never output q29 or torques. Closure fractions 0–1 are commands, not aperture or force. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

## Visual geometry and verification

Identify the white rectangular target independently of rounded/irregular distractors. Ray-plane projection is not depth. Use calibrated stereo correspondence; reject shadows, occlusions and inconsistent reprojections. A fitted cuboid must match both views; dimensions and planes remain estimates. Re-localize after contact, including table-edge margin.

Use current native distal mesh bounds and link origins, not cube capsules. Bounds are conservative ranges, not contact surfaces. Check the whole visible hand and distal geometry through approach, rotation and closure. Establish clearance before crossing the box. Requested attitude may differ materially from achieved attitude; recompute geometry.

Close gradually only after reviewing thumb/index-middle opposition. Test 10–20 mm lift and one independent original-target hold. Wrist ascent, commanded closure, target_reached and pixel overlap do not prove grasp. Require box-hand co-motion; after loss reopen with clearance and reassess. Complete 8 cm lift only after evidence supports retention.

## Task-specific evidence: episode0001, unsuccessful

Initial stereo cuboid fit estimated top 0.619 m, support 0.424 m, thickness 0.062 m, width 0.155 m, height 0.195 m, yaw -0.096 rad; residual 0.42 px. These are reset-specific RGB estimates, not constants.

Raised right-hand approach tracked position well. Isolated rotations 008–014 reduced attitude residuals compared with combined motions, but at forward/inward reach 016–018 attitude bias persisted despite an isolated correction. Do not prescribe isolated rotation as a universal fix.

Descents 020/021/024 undertracked; opening and changing active orientation did not resolve the downward stall. Causes remain uncertain: contact/clearance and pose-dependent tracking were not fully separated. Do not keep pressing downward or close merely because the wrist target was reached.

Closures 025/026 at 0.30/0.40 tipped the box. Probe 027 and hold 028 were ambiguous;029 raised the wrist 21.6 mm while the box settled and hand separated, rejecting retained grasp.030–032 opened and withdrew; box was flat near the front edge. Feet remained supported. No native success or verified 8 cm lift occurred; finish_attempt ended the episode as policy_declared_stall.

Next hypothesis, unverified: settle orientation outside the box, test side-clear descent, and place thumb visibly below the top before closure. If reach bias persists, change approach direction or hand. Do not promote this failed trajectory or 0.20 preclosure to a recipe.

## Termination and learning

Await complete service responses; reasoning pauses simulation. Stop physical actions on rollout_finished. After at least three actions an evidenced stall may use finish_attempt with a changed hypothesis; it is never success. Avoid idle budget-filling.

After termination submit complete skill_update with concise lesson/change_summary and existing public evidence paths, within all caps. Keep these corrections task_specific. Shared proposals require cross-task validation and grasp regression before promotion; local revisions never overwrite shared core.
