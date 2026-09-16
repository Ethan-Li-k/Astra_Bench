---
name: loco-manip-direct
description: Learn native SIMPLE cracker-box grasping from public visual evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Identify the cracker box by visible geometry, grasp with a Dex3 hand, and lift it at least8cm above its initial height while standing. Require one independently reset native success. Assess native height success, box-hand co-motion and visible support separately.

Read workspace.json, task_specification, SKILL.md and experience_read. Use workspace Python; install nothing. Use only listed self-experience, cited public evidence, RGB, named robot state, calibration and robot geometry. No demonstrations, hidden object/contact state, evaluator/runtime inspection, other simulators or hardware. Act only through registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints, closure commands and native geometry. Before acting, experience_select records sources, applicability, adaptations and rejected transfers. Re-select on changed failure modes; retrieve selectively. Shared episodes437/438 support retrieve-test-observe-correct, gradual closure, probes and independent holds. Validate their coordinates, geometry, attitudes and closures afresh.

Use one reviewed waypoint, latest observation path/ID and unique request ID. In reason state problem, goal, evidence, purpose, expected change and errors to avoid. After every action inspect fresh RGB and actual poses. Separate targets, tracking, contact hypotheses and progress. Record uncertainty and next hypothesis. Never blindly replay or repeat unchanged failures.

Include all four absolute positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect0.03m translation,0.10rad rotation and0.5–3s duration limits. Keep feet supported; inspect drift. Never output q29 or torques. Closure fractions are commands, not aperture or force. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

## Geometry and verification

Distinguish the white box from rounded distractors. Ray-plane projection is not depth. Use calibrated stereo; reject shadows, occlusion and inconsistent reprojections. Small disparity errors bias height; cuboid estimates must match both views. Compare visible landmarks against current calibrated reprojections during entry; head motion changes pixels, and occluded corners are uninformative. Relocalize after settling and check table-edge margin.

Use native distal bounds and link origins, not cube capsules. Bounds are conservative ranges, not contact surfaces; thumb-bound minima below the top do not prove useful contact depth. Read hand_collision_model selectively. Mesh vertices include geom-to-body transforms; apply current body_poses_world. Handle primitive half-sizes and transforms separately. Review wrist/palm, proximal and distal clearance throughout rotation, entry and closure at the achieved attitude.

Orientation-only control can improve angle while drifting position by centimetres. Inspect position before reactivation. Position tracking does not imply angle tracking. Compare achieved roll/pitch/yaw to a fixed goal; repeated measured-yaw increments can accumulate roll/pitch bias. High-side flattening may disappear during descent. Establish a compatible low pose before committing to entry.

Review thumb versus index/middle opposition before contact closure. Free-space closure characterizes geometry, not a preclosure recipe. Test a10–20mm lift and separate original-target hold. Wrist ascent, closure, target_reached and overlap do not prove grasp. Require box-hand co-motion and visible support before further lift. After loss, reopen with clearance.

## Task-specific evidence

Episodes0001–0005 ended through finish_attempt without native success or verified retention. Backend SimpleLiveSim, not Isaac. Prior versions preserve detailed failures.

0001: descent undertracked; .30/.40 closures tipped box.
0002: side rotation tracked, but low/forward and orientation-free/coordinated descent failed; entry displaced box and probe/hold showed settling.
0003: rolled descent lowered47mm with attitude drift; low entry displaced box, high entry left shallow opposition. Closure.30 tipped it; probe/hold rejected retention.
0004: flattening failed during descent; lower targets undertracked. Free-space.15/.25 showed shallow opposition. Near-zero-yaw entry displaced box despite distal clearance; no contact closure/lift.

0005:25 actions,87.28s. Right yaw goal1.5rad failed; achieved yaw peaked.47. Position-active013/018/020 tracked within1.1/1.9/2.4mm but angle errors were.065/.122/.105rad. Orientation-only015 shifted wrist about38mm. Free-space.15 closure021 supplied whole-hand geometry. Descents022/023 lowered27.6/19.1mm; position-only024 lowered9mm of17.3mm, with11.5mm residual. Pitch steepened.488 to.659. Coarse stereo top matches were inconsistent and rejected. Open withdrawal025 separated hand; box upright, feet supported, drift under.7mm. No contact closure/lift.

Next hypothesis: test left inward yaw after establishing a low side-clear pose, using fixed-attitude corrections. Validate whole-hand opposition and calibrated box edges before entry. Do not mirror coordinates, replay rolled forward entry or close harder. No successful box recipe exists.

## Termination and learning

Await complete responses; reasoning pauses simulation. Stop physical actions on rollout_finished. After three actions, finish_attempt may end an evidenced stall with a changed hypothesis; never count it as success or fill budget with idle holds.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence paths within all caps. Keep corrections task_specific; shared proposals need cross-task validation and grasp regression. Never overwrite shared core. Preserve prior versions and failures; host owns recording/export.
