---
name: loco-manip-direct
description: Learn visual apple placement using task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Pick up the apple beside the bowl, carry above its opening, release inside and verify retention after hand withdrawal while standing. Preserve native SIMPLE outcome separately: accumulated apple-bowl contact does not prove placement inside.

Use registered physics services and loco_start exactly once. No demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets, other simulators or hardware. Read only listed campaign self-experience and robot geometry. Use the exact workspace interpreter; install nothing. Store artifacts only in designated RSI paths.

## Retrieve and select

Selectively read relevant experience and cited public trajectories. Before acting call experience_select with source IDs, applicability, adaptation and rejected details; reselect when failure mode changes. Grasp437/438 transfer retrieve-test-observe-correct, gradual closure and independent lift verification, not apple coordinates, dimensions, table height, closure or attitude. Preserve decisions and uncertainties in public reasons.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joint names, fingers and closure. Use one reviewed waypoint, latest observation path and unique request ID. State evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. After every action inspect RGB and actual poses. Separate requested target, tracking, contact hypothesis and progress.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect 0.03m translation, 0.10rad rotation and 0.5-3s duration limits. Never output q29 or torques. Map joints by name. Grippers are ramped fractions: zero open, one closed.

Geometry tools calculate; scalebfm_act executes. Wrist frames are not calibrated TCPs. Check whole-hand opening, closure and rotation sweeps using current named geometry and fingers. Distal mesh bounds are not contact surfaces. Quaternion targets track only with orientation active. Preserve nonmoving references instead of accumulating measured bias; report position and attitude errors independently, including on timeout. Monitor actual ankles and body-camera response; arbitrary foot displacement is not verified walking.

## Visual manipulation

Use calibrated stereo correspondences with reprojection and uncertainty checks. Ray-plane projection is not depth. Reject shadows, clipped silhouette centres, featureless patches and inconsistent edges. Recompute camera geometry after body motion. Robot projections explain nonvisibility but do not replace visible manipulation evidence.

Acquire a visible, clear pregrasp before inward approach. Align opposing surfaces through the anticipated closure sweep, not merely open fingertips. Close gradually and test a short lift. Verify apple motion relative to table in both views, then independently observe/hold. Closure, wrist motion, target_reached and overlapping pixels prove neither grasp nor placement. After failed enclosure/slip, reopen with clearance and relocalize. Carry only a verified grasp above the rim; lower toward the visible opening, release, withdraw and inspect retention/support unless terminated.

## Task-specific evidence

Episodes0001/0002 stalled after15/19 actions without visible hands or grasp; ascent/rotation and fixed-height side reach undertracked. Accurate yaw did not clear the inward thumb; no absolute reach limit was established. Rough bowl coordinates were unreliable.

Episode0003 ended after70 actions in policy_declared_stall, native in_progress. Observations0014/0027/0050 show the clearance route: localize near edge, retreat behind it, ascend with whole-hand clearance, cross high, then move inward until real fingers enter both cameras.

Dark shapes in0036-0039 were shadows, corrected by stereo table-height triangulation and robot projections; actual fingers appeared later. Do not preserve uncertain stereo coordinates after body motion or possible apple pushes.

Actions0060-0062 ramped closure0/.15/.35/.5. Two18mm wrist lift probes produced no verified apple-table separation; reopening0065 exposed apple beside bowl. Closed thumb bounds were about29mm higher than middle: open-hand alignment had not ensured opposing closure surfaces. Negative-Y pitch at high pose0066 tracked2.5mm/.0037rad, but lower approach0068 timed out2.25mm/.169rad. Isolated0069 correction timed out1.13mm/.085rad against an.08rad increment. Upward reopening0070 recovered5.1mm/.043rad; final ankles erred1.93/1.69mm. No grasp, carry or placement was verified.

Next hypothesis, unvalidated: retrieve the rear/high visibility route, test partially closed opposing-surface attitude while high, acquire thumb visibility, then lower only with actual attitude tracking and whole-hand clearance. Relocalize after possible pushes; require independent lift retention. Do not replay saturated low corrections or promote closure0.5 as successful.

## Termination and learning

Stop physical actions immediately on rollout_finished. After three actions, finish_attempt may document an evidenced stall and changed hypothesis; it is not success. Do not fill the budget with idle holds. Separate local construction errors, explicit service errors and uncertain transport; never blindly retry uncertain actions.

After termination submit complete skill_update, concise lesson/change_summary and existing public rollout evidence from this episode. Check every length cap and retain versions. Keep task-specific rules separate from shared_candidate proposals; promote only after cross-task validation and grasp regression. Keep learning separate from frozen evaluation.
