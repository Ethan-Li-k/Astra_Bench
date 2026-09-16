---
name: loco-manip-direct
description: Learn visual apple placement using task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Pick up the apple, carry above the bowl opening, release inside and verify retention after hand withdrawal while standing. Preserve native SIMPLE outcome separately: accumulated apple-bowl contact does not prove placement inside.

Use registered physics services and loco_start exactly once. No demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets, other simulators or hardware. Read only listed campaign self-experience and robot geometry. Use the exact workspace interpreter; install nothing. Store artifacts only in designated RSI paths.

## Retrieve and select

Selectively retrieve relevant experience and cited public trajectories. Before acting call experience_select with source IDs, applicability, adaptation and rejected details; reselect when failure mode changes. Grasp437/438 transfer retrieve-test-observe-correct, gradual closure and independent lift verification, not apple coordinates, dimensions, height, closure or attitude. Record problem, goal and uncertainties in public reasons.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joints, fingers and closure. Use one reviewed waypoint, latest observation path and unique request ID unless the current interface explicitly enables continuous chunks. State evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. Inspect RGB and actual poses after every action.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect current limits: 0.03m translation, 0.10rad rotation, 0.5-3s duration. Never output q29 or torques. Map joints by name. Grippers are ramped fractions: zero open, one closed; inspect actual finger joints after ramps.

Geometry tools calculate; scalebfm_act executes. Wrist frames and distal-bound centroids are not calibrated grasp centres. Review opening, closing, rotation and translation sweeps. Inspect individual bounds alongside aggregate boxes with fictitious cross-finger corners; neither supplies exact contact geometry. Preserve nonmoving references instead of accumulating measured bias. Activate orientation tracking explicitly; report position and attitude errors separately, including timeouts. Monitor ankles and camera/body response; arbitrary foot displacement is not verified walking.

## Visual manipulation

Use calibrated stereo correspondences with reprojection and uncertainty checks. Ray-plane projection is not depth. Reject shadows mistaken for fingers, clipped silhouette centres, featureless patches and occluded/inconsistent matches. Recompute geometry after body motion or possible pushes. Robot projections explain nonvisibility but cannot replace visible manipulation evidence.

Acquire a visible, clear pregrasp. Inspect opposing curved pads through anticipated closure, not merely open fingertips or mesh-centroid midpoints. Shape partial closure while high; lower only after actual attitude and whole-hand clearance checks. Close gradually, test a short lift, then independently observe retention if plausible. Verify apple motion relative to table in both views. Closure, wrist motion, target_reached and overlapping pixels prove neither grasp nor placement. After failed enclosure/slip, reopen with clearance and relocalize.

Carry only a verified grasp above the rim. Lower toward the visible opening, release, withdraw and inspect apple retention/support unless terminated.

## Task-local evidence and next test

Episodes0001/0002 lacked visible hands. Episode0003 established retreat behind the visually localized near edge, ascent, high crossing and inward travel; observations0014/0027/0050 are route evidence. Closure through.5 and two18mm probes failed; low attitude corrections saturated, while high negative-Y pitch tracked. 

Episode0004 ended after63 actions/162.92s as policy_declared_stall, native in_progress. Direct rear travel at initial Y stalled on3; outboard preparation4-6 restored rear access. Rear ascent10-22 and inward travel23-29 produced bilateral hand visibility by28/29. High partial closure30 and pitch31 tracked, but lower approaches36/37/52 again developed attitude errors. Isolated pitch51 tracked. Improved closing-height alignment did not yield grasp.

Four enclosure/lift trials40,46-47,55,62 at closure.48/.48/.58/.65 failed verification despite rear, height and transverse corrections. Trial2 included an independent hold. Final reopening63 exposed apple beside bowl; textured crown triangulation remained near.932m. Final wrist error7.01mm/.0799rad; ankles1.68/1.58mm. No placement occurred.

Next hypothesis, unvalidated: retrieve the shorter visible route, reconstruct the opposing curved pad region at actual partial closures, then test one wrist-local offset at fixed closure and tracked attitude. Centroid alignment and tested closure fractions are not successful recipes. Tabletop stereo and finger sweeps constrain descent; withhold targets lacking clearance.

## Termination and learning

Stop physical actions immediately on rollout_finished. After three actions, finish_attempt may document an evidenced stall and changed hypothesis; it is not success. Do not fill the budget with idle holds. Separate local construction errors, explicit service errors and uncertain transport; never blindly retry uncertain actions.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence from this episode. Check all length caps and retain versions. Keep task-specific rules separate from shared_candidate proposals; promote only after cross-task validation and grasp regression. Keep learning separate from frozen evaluation.
