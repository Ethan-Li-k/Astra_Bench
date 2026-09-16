---
name: loco-manip-direct
description: Learn visual apple placement from task-local physical evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Pick up the apple, carry above the bowl opening, release inside and verify retention after withdrawal while standing. Preserve native SIMPLE outcome separately: accumulated apple-bowl contact does not prove placement inside.

Use registered physics services and loco_start exactly once. No demonstrations, hidden object/contact state, evaluator inspection, runtime changes, resets or other simulators/hardware. Read only listed self-experience and robot geometry. Use the exact workspace interpreter; install nothing. Store artifacts only in designated RSI paths.

## Retrieve and select

Retrieve relevant public self-experience; call experience_select before acting and reselect when failure changes. Record source IDs, applicability, adaptation and rejections. Grasp437/438 transfer retrieve-test-observe-correct, gradual closure and independent lift verification, not apple coordinates, dimensions, height, closure or attitude. Record problem, goal and uncertainties in public action reasons. Disclose semantic human feedback; assisted runs are not unaided Direct.

## Observe and command

Inspect fresh stereo RGB, calibration, named measured/reference poses, joints, fingers and closure. Use one reviewed waypoint, latest observation path and unique request ID unless observation explicitly permits chunks. State purpose and expected visible change. Await complete responses; simulation pauses during reasoning. Inspect RGB and actual poses after every action.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Limits: 0.03m translation, 0.10rad rotation, 0.5-3s duration. Never output q29 or torques. Map joints by name. Grippers ramp from zero open to one closed; command0 does not establish actual opening.

Preserve nonmoving references, including horizontal targets during vertical probes. Activate orientation tracking explicitly; report position and attitude errors separately, including timeouts. Isolate rotation when travel corrupts attitude. Monitor ankles/body-camera; arbitrary ankle reference shifts are not verified walking.

## Geometry and vision

Wrist frames and bound centroids are not grasp centres. Transform individual robot collision surfaces at measured joints. Review opening, closure, rotation and translation sweeps at measured and target attitudes, including palm/proximal links. Aggregate bounds contain fictitious cross-finger corners; meshes do not prove contact. Withhold motions lacking clearance under tracking and stereo uncertainty.

Audit camera reprojection against several anatomically identified robot surfaces in both views before trusting metric depth. Episode7 observations33/35/36/37 supported an empirical image correction fx/fy~1.275, cx320, cy189; square-pixel projection disagreed. Treat this robot-only fit as unvalidated; recheck across poses and reject occluded fits. Never assume it replaces calibration.

Use stereo correspondence, reprojection and uncertainty checks; ray-plane projection is not depth. Even perfect correlation and zero ray residual can match the wrong feature. Reject shadows, clipped centres and inconsistent anatomy. Crown features locate surface, not object centre. Relocalize after body motion or possible pushes. Robot projections cannot replace visible manipulation evidence.

## Enclosure and verification

H001004 supersedes exploratory partial closure: keep the hand open throughout alignment until apple side contour and opposing inner curved pads establish enclosure in both views. A projected pad envelope is necessary, insufficient evidence; future closed-mesh overlap alone does not qualify. If occluded or outside, change open alignment/view. Do not substitute fingertips, crown-to-centroid equality or a universal palm-height rule.

Shape attitude while high and open. Descend only with verified actual attitude and whole-hand clearance. Close gradually, probe a short vertical lift, then independently verify apple-table separation and sustained hand-object co-motion in both views. Joint divergence, closure, wrist motion and target_reached do not prove grasp. After failure reopen with clearance, inspect actual opening and relocalize.

Carry only a verified grasp above the rim. Lower toward the visible opening, release, withdraw and inspect retention/support unless terminated.

## Task-local evidence and next test

Episodes3-6 provide rear/ascent and isolated local-X roll evidence, not successful enclosure. Episode7 used H001004, no demonstration, SimpleLiveSim. It ended at122 actions on episode_step_budget; native in_progress, no placement. Four closure/lift trials failed: separation at54/65/111/119; withdrawal122 shows apple beside bowl. Quarter-roll occluded the apple; changing roll/height did not fix capture.

Next unvalidated test: distinguish lateral/depth/height error using visible apple/pad surfaces, robot reprojection auditing and one open perturbation. Do not repeat these failed poses or chase height alone.

## Termination and learning

Stop actions immediately on rollout_finished. finish_attempt records a stall and changed hypothesis, not termination; use its observation/next_call to test a changed safe approach until native termination, system/safety fault or budget. No idle budget filling. Separate local construction errors, explicit service errors and uncertain transport; never blindly retry uncertain execution.

After termination submit complete skill_update with concise lesson/change_summary and existing episode evidence. Check every length cap and retain versions. Keep task-specific learning separate from shared_candidate proposals and frozen evaluation; promote only after cross-task validation and grasp regression.
