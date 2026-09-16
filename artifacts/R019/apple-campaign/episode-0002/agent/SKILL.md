---
name: loco-manip-direct
description: Learn visual apple placement using task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, its task_specification, assembled SKILL.md and experience_read. Pick up the apple beside the bowl, carry it above the opening, release it inside, and verify retention after hand withdrawal while standing. Preserve native SIMPLE outcome separately from visible completion: accumulated apple-bowl contact alone does not establish placement inside.

Use registered services for physics; loco_start exactly once. No human demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets, other simulators or hardware. Read only listed campaign self-experience and robot geometry. Use the exact workspace interpreter; install nothing or modify existing environments. Store new artifacts only in designated RSI paths.

## Retrieve and select

Read relevant local experience and cited public trajectories selectively. Before acting call experience_select with source IDs, applicability, adaptation and rejected details; reselect when the failure mode changes. Prior grasp437/438 support retrieve-test-observe-correct, gradual closure and independent lift verification. They do not supply apple coordinates, table height, dimensions, closure, grasp attitude or task success. Preserve decisions and uncertainties in public reasons/notes.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joint names, fingers and closure. Use one reviewed waypoint, the latest observation path and a unique request ID. State evidence, purpose and expected observable change. Await complete responses; simulation pauses during reasoning. After every action inspect RGB and actual poses. Separate requested target, tracking, contact hypothesis and task progress.

Include absolute world positions in metres and unit wxyz quaternions for left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link and right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Obey reported 0.03m translation, 0.10rad rotation and 0.5-3s duration limits. Never output q29 or torques. Map joints by name. Grippers are ramped closure fractions: zero open, one closed.

Geometry tools calculate; scalebfm_act executes. Wrist frames are not calibrated TCPs. Check the entire hand using current named geometry and finger state, including opening/closing sweeps. A target quaternion is tracked only when orientation is active. Avoid reanchoring inactive components to biased measurements. Check actual ankle/body response; arbitrary foot displacement is not verified walking.

## Visual manipulation

Use calibrated stereo correspondences with reprojection and uncertainty checks. Ray-plane projection is not depth. Reject shadows, clipped silhouette centres, featureless patches and inconsistent edges. Recompute camera geometry after body motion. Project known robot points to explain nonvisibility, but require independent visible evidence before claiming manipulation.

Acquire a visible, clear pregrasp before moving inward. Align opposing finger surfaces around the apple, close gradually and test a short lift. Verify apple motion relative to the table in both views, followed by an independent observation/hold. Closure, wrist motion, target_reached and overlapping pixels prove neither grasp nor placement. After slip, reopen with clearance and relocalize. Carry only a verified grasp above the bowl rim, lower toward its visible opening, release and withdraw. Inspect retention and standing posture unless termination prevents further actions.

## Task-specific evidence: apple episode0001

Fifteen actions ended in policy_declared_stall, with native outcome in_progress and no grasp. Initial apple/bowl were clipped at the lower image boundary; hands never became visible. Vertical wrist progress did not establish whole-hand clearance. Action3 combined rise/rotation timed out and ankles drifted roughly29/43mm from references. Action7 requested20mm forward/22mm up but gained only3/2mm. Retreat then ascent recovered elevation without restoring simultaneous hand/apple visibility.

Position-only motion allowed substantial attitude drift. Actions13/14 reached position within3mm while attitude errors remained85/117mrad; action15 had18mm position residual. Inspect position and orientation separately even on timeout. Initial rough bowl-rim stereo correspondences were unreliable; textured facet matching changed estimated disparity. Do not preserve rough coordinates as scene facts.

Next hypothesis, unvalidated: acquire visibility earlier with a small isolated forward reach and active measured attitude, then separately test attitude correction. Project current wrist/fingertip candidates, verify full-hand clearance and fresh apple localization before inward motion. Do not replay the failed cumulative rise sequence.

## Termination and learning

Stop physical actions immediately on rollout_finished. After at least three actions, finish_attempt may document an evidenced stall and changed hypothesis; it is not success. Do not fill the budget with idle holds. Preserve explicit service errors separately from local construction errors and uncertain transport; never blindly retry an uncertain action.

After termination submit a complete skill_update, concise lesson/change_summary and existing files from this episode's public rollout as evidence. Check all length caps and retain versions. Mark task-specific rules separately from shared_candidate proposals; promote shared rules only after cross-task validation and grasp regression. Keep learning separate from frozen evaluation.