---
name: loco-manip-direct
description: Learn visual apple placement from task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Pick up the apple, carry above the bowl opening, release inside and verify retention after withdrawal while standing. Preserve native SIMPLE outcome separately: accumulated apple-bowl contact does not prove placement inside.

Use registered physics services and loco_start exactly once. No motion demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets, other simulators or hardware. Read only listed self-experience and robot geometry. Use the exact workspace interpreter; install nothing. Store artifacts only in designated RSI paths.

## Retrieve and select

Retrieve relevant experience and public trajectories. Before acting call experience_select with source IDs, applicability, adaptation and rejected details; reselect when failure changes. Grasp437/438 transfer retrieve-test-observe-correct, gradual closure and independent lift verification, not apple coordinates, dimensions, height, closure or attitude. Record problem, goal and uncertainties in public reasons. Disclose semantic human feedback exposure; do not label it unaided Direct.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joints, fingers and closure. Use one reviewed waypoint, latest observation path and unique request ID unless observation explicitly enables continuous chunks. State purpose and expected visible change. Await complete responses; simulation pauses during reasoning. Inspect RGB and actual poses after every action.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Limits: 0.03m translation, 0.10rad rotation, 0.5-3s duration. Never output q29 or torques. Map joints by name. Grippers ramp from zero open to one closed; equal fractions can produce different actual joints after different histories.

Geometry tools calculate; scalebfm_act executes. Wrist frames and bound centroids are not grasp centres. Transform individual robot collision surfaces at measured joints; neither bounds nor meshes reveal contact. Review opening, closing, rotation and translation sweeps at measured and target attitudes, including palm/proximal links. Aggregate bounds contain fictitious cross-finger corners. Withhold motions lacking clearance under tracking and stereo uncertainty.

Preserve nonmoving references, including horizontal targets during vertical probes. Activate orientation tracking explicitly; report position and attitude errors separately, including timeouts. Monitor ankles and body-camera response; arbitrary foot displacement is not verified walking.

## Visual manipulation

Use calibrated stereo, reprojection and uncertainty checks; ray-plane projection is not depth. Verify anatomical identity and several consistent features. Even perfect patch correlation and zero ray residual can match the wrong feature. Reject shadows, clipped centres, occlusion and inconsistent matches. Crown features locate surface, not object centre. Robot projections explain nonvisibility but cannot replace visible manipulation evidence. Relocalize after body motion or possible pushes.

Acquire a clear pregrasp exposing apple side contour and opposing inner curved pads. Require apple inside the anticipated projected pad envelope in both views before closure; this is necessary, not sufficient evidence. If outside or occluded, change the open-hand alignment/view before further closure. Do not substitute fingertips, crown-to-centroid equality or a uniform palm-height rule.

Shape partial closure while high; descend only with verified actual attitude and whole-hand clearance. Close gradually, probe a short lift, then independently observe retention if plausible. Verify apple motion relative to table in both views. Closure, wrist motion, target_reached and overlapping pixels prove neither grasp nor placement. After failure, reopen with clearance and relocalize.

Carry only a verified grasp above the rim. Lower toward the visible opening, release, withdraw and inspect retention/support unless terminated.

## Task-local evidence and next test

Episodes0003-0005 provide rear/ascent route evidence; their low enclosure/lift trials failed.

Episode0006 ended at93 actions/223.54s: policy_declared_stall, native in_progress. Bilateral fingers appeared22. High isolated local-X rolls tracked well; quarter-roll51 reached1.34mm/.0106rad. Combined travel sometimes produced large attitude errors. Four enclosure/lift trials61/74/82/89 failed; independent lift90 exposed separation. Open withdrawal91-93 left apple beside bowl. No carry or placement. H001 semantic feedback was exposed.

The failed trials show that accurate wrist attitude and partial closure do not fix unseen enclosure. Next hypothesis, unvalidated: expose side contour and inner pads, reconstruct their visible surfaces at actual joints, then distinguish lateral versus depth error with one open-hand perturbation. Retain high attitude shaping; reject these low closure poses as a successful policy.

## Termination and learning

Stop physical actions immediately on rollout_finished. After three actions, finish_attempt may document an evidenced stall and changed hypothesis; it is not success. Do not fill budget with idle holds. Separate local construction errors, explicit service errors and uncertain transport; never blindly retry uncertain actions.

After termination submit complete skill_update, concise lesson/change_summary and existing episode evidence. Check every length cap and retain versions. Keep task-specific rules separate from shared_candidate proposals; promote only after cross-task validation and grasp regression. Keep learning separate from frozen evaluation.
