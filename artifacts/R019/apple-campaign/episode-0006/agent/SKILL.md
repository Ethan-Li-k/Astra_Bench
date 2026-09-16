---
name: loco-manip-direct
description: Learn visual apple placement from task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Pick up the apple, carry above the bowl opening, release inside and verify retention after withdrawal while standing. Preserve native SIMPLE outcome separately: accumulated apple-bowl contact does not prove placement inside.

Use registered physics services and loco_start exactly once. No demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets, other simulators or hardware. Read only listed self-experience and robot geometry. Use the exact workspace interpreter; install nothing. Store artifacts only in designated RSI paths.

## Retrieve and select

Retrieve relevant experience and public trajectories. Before acting call experience_select with source IDs, applicability, adaptation and rejected details; reselect when the failure mode changes. Grasp437/438 transfer retrieve-test-observe-correct, gradual closure and independent lift verification, not apple coordinates, dimensions, height, closure or attitude. Record problem, goal and uncertainties in public reasons.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joints, fingers and closure. Use one reviewed waypoint, latest observation path and unique request ID unless the observation explicitly enables continuous chunks. State purpose and expected observable change. Await complete responses; simulation pauses during reasoning. Inspect RGB and actual poses after every action.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Limits: 0.03m translation, 0.10rad rotation, 0.5-3s duration. Never output q29 or torques. Map joints by name. Grippers ramp from zero open to one closed; equal commanded fractions can have different actual finger configurations after different histories. Inspect actual joints and geometry.

Geometry tools calculate; scalebfm_act executes. Wrist frames and distal-bound centroids are not calibrated grasp centres. Review opening, closing, rotation and translation sweeps at both measured and target attitudes. Inspect individual bounds; aggregate boxes contain fictitious cross-finger corners. Neither supplies exact contact geometry. Withhold motions lacking clearance under tracking and stereo uncertainty.

Preserve nonmoving references rather than accumulating measured bias. Activate orientation tracking explicitly; report position and attitude errors separately, including timeouts. Monitor ankles and body-camera response; arbitrary foot displacement is not verified walking.

## Visual manipulation

Use calibrated stereo correspondences, reprojection and uncertainty checks; ray-plane projection is not depth. Reject shadows, clipped centres, featureless or occluded patches and inconsistent matches. High patch correlation can match the wrong finger: check anatomical identity and consistency with projected robot geometry. Projections explain nonvisibility but cannot replace visible manipulation evidence. Relocalize after body motion or possible pushes.

Acquire a visible, clear pregrasp. Inspect opposing curved pads through anticipated closure, not merely fingertips or mesh-centroid midpoints. Shape partial closure while high; descend only with verified actual attitude and whole-hand clearance. Close gradually, probe a short lift, then independently observe retention if plausible. Verify apple motion relative to table in both views. Closure, wrist motion, target_reached and overlapping pixels prove neither grasp nor placement. After failed enclosure/slip, reopen with clearance and relocalize.

Carry only a verified grasp above the rim. Lower toward the visible opening, release, withdraw and inspect apple retention/support unless terminated.

## Task-local evidence and next test

Episodes0001/0002 lacked visible hands. Episode0003 established rear retreat, ascent and high inward travel; observations0014/0027/0050 are route evidence. Episode0004 shortened visibility to28/29 but four enclosure/lift trials failed. 

Episode0005 ended after72 actions/186.66s, policy_declared_stall, native in_progress. Rear/outboard preparation and earlier negative-Y pitch produced bilateral fingers22 and full thumb24. Isolated local-X rolls tracked;47-59 brought finger spread approximately horizontal. Inward/pitch61 and isolated pitch62 timed out at.175/.096rad. Low descents38/44 also developed attitude error.

Lift40/46 at.45 and69 at.56 failed verification;70 was an independent1.5s hold. Withdrawal72 exposed apple beside bowl; crown stereo(452,330)/(392,330) gavez.93305m. No carry or placement. Actual-attitude bounds sometimes approached tabletop more closely than target-attitude predictions; service acceptance does not establish clearance.

Next hypothesis, unvalidated: establish a visible camera corridor and reconstruct opposing inner pad surfaces at actual joints. Shape downward pitch before inward quarter-roll travel, then test one pad-frame offset only with tracked attitude and conservative sweep clearance. Do not repeat low closure based on centroid equality.

## Termination and learning

Stop physical actions immediately on rollout_finished. After three actions, finish_attempt may document an evidenced stall and changed hypothesis; it is not success. Do not fill the budget with idle holds. Separate local construction errors, explicit service errors and uncertain transport; never blindly retry uncertain actions.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence from this episode. Check every length cap and retain versions. Keep task-specific rules separate from shared_candidate proposals; promote only after cross-task validation and grasp regression. Keep learning separate from frozen evaluation.
