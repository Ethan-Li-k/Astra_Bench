---
name: loco-manip-direct
description: Learn measured-table cracker-box acquisition from public evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Identify the cracker box visually, grasp with Dex3, and lift at least3cm above its initial height while standing. Report native height, retained support and box-hand co-motion separately.

Read workspace.json, task_specification, SKILL.md and experience_read. Use workspace Python; install nothing. Only listed self-experience, cited public trajectories, RGB, calibration, named robot state and robot geometry are allowed. No demonstrations, hidden state, evaluator/runtime inspection, other simulators or hardware. Use registered services for physics.

## Retrieve and control

Call loco_start once. Inspect stereo, calibration, measured/reference poses, joints and closure. Before acting, experience_select records sources, applicability, adaptations and rejected transfers; reselect when failure mode changes. Transfer437/438 and bendpick0006 verification methods, never their coordinates or assumed attitudes.

Review each action with latest observation and unique request ID. Use one waypoint unless chunks are enabled; obey current bounds and inactive-reference contract. Include all four named wrist/ankle absolute world positions in metres and unit wxyz quaternions. Declare active position/orientation. Never output joints or torques. Closure0=open,1=closed is neither aperture nor force. Wrist frames are not calibrated TCPs.

Inspect fresh RGB/poses after execution. Separate targets, tracking, contact and progress. Monitor ankle translation/yaw/height. Change failed tests; never replay uncertain actions.

## Geometry and acquisition

Use current render_intrinsics and calibrated pixel convention. Ray-plane projection is not depth. Reject occluded/rounded-corner mismatches. Reproject the fitted box in both views before entry; reconstruct after displacement. A cropped view plus an old fit is insufficient.

Use native palm/proximal/distal meshes and current body poses, not cube capsules. Review whole-hand clearance through rotation, translation and closure with uncertainty margins. Finish and inspect calculations before execution; never chain calculation into action without reviewing its result. Reject predicted interference. 

Close only after visible opposition and geometry support enclosure. Close gradually; test10–20mm lift and a separate original-target hold. Require box-hand co-motion and retained support. Overlap, wrist ascent, target_reached and tipping are insufficient. After separation reopen with clearance and change geometry, not merely strength.

## Task-specific evidence: episode0001

SimpleLiveSim/MuJoCo, not Isaac:65 actions ended at episode_step_budget; native_outcome=in_progress, zero successes, no verified retained lift. Preserve calls001–065/NOTES; distinguish budget termination from native failure.

High/retracted raises produced negative elbow, medial/attitude undertracking and support drift that cropped the box. Orientation-only tests changed angles but drifted position by centimetres. Lower diagonal stages tracked better; neither is a grasp recipe. Two backward ankle tests did not establish stepping. Feet drifted substantially despite near-support height.

035 predicted thumb interference but executed before calculation review;036 showed tipping/displacement. Reject this planning pattern. Tilted-box side approaches and.35/.40/.45 closures failed lift/hold verification; never treat these poses as successes. Next reset: validate stereo reprojection early, preserve useful view, gate clearance calculations and establish opposition before probing.

## Continuity and learning

Await complete responses; reasoning pauses simulation. finish_attempt records a stall and changed hypothesis, not termination. Continue changed tests until rollout_finished or native safety/system/budget termination; no idle budget filling. Submit task_specific skill_update with lesson/change_summary and public evidence; preserve versions/failures and caps. Shared promotion requires cross-task validation and grasp regression.
