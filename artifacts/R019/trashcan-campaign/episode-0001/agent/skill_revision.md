---
name: loco-manip-direct
description: Use public visual control evidence with task-specific adaptation.
---

## Contract and sources

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, SKILL.md and experience_read. Current task and observed interface override historical candidates. Use only allowed public evidence, RGB, camera calibration, named robot state and robot geometry. No hidden object/contact/reward state, demonstrations, resets or other simulators. Use the exact workspace interpreter; install nothing.

Record 当前问题 / 总目标 / 不可重犯的错误 and concise observed results, uncertainty and next test in notes. Call loco_start once. Inspect both images, measured/reference poses, joints, grippers and limits. Before acting, experience_select names source IDs, applicability, adaptations and exclusions; reselect when failure mode changes. Retrieve relevant versions and cited public actions selectively. Grasp437/438 support retrieve-adapt-observe; their coordinates, capsule geometry and closure do not transfer.

## Execute and verify

Use the latest observation and unique request ID; state evidence, purpose and predicted observable change. Supply all four named wrist/ankle poses in world metres with unit wxyz quaternions. Declare active position/orientation; retain inactive components per current contract. Never command joints or torques. Grippers ramp from 0=open to 1=closed; closure is not contact evidence. Wrist frames and mesh bounds are not calibrated TCPs.

Use current single-waypoint limits. Continuous chunks require explicit enablement and must respect knot, total-duration, translation and rotation bounds. Reobserve after each action. Separate requested targets, measured tracking, contact hypothesis and task progress. Inspect intermediate robot traces when needed. Position arrival can coexist with orientation drift; timeout is not automatically physical failure. Change a justified variable after an ineffective probe.

Use render_intrinsics and pixel centres. Ray-plane projection is not depth; reject uncertain stereo matches, shadows and occlusion. Check whole-hand clearance using current posture/robot geometry. Establish visible enclosure before grasp closure; verify manipulation with a short probe and independent observation. Ankle rise is not sole clearance or proof of walking. Unload before repositioning after reach saturation.

Await complete inference/service responses; physics pauses during reasoning. Continue until host terminal, safety/system fault or physical budget. finish_attempt records a nonterminal stall and changed hypothesis; test it in the same episode. Never replay uncertain executed actions or spend budget on repeated idle holds. Stop motion immediately on rollout_finished.

## Trash-can evidence — task specific

Episode0001 reached native success in five actions, 16.62 active simulation seconds. Initial stereo placed the near lid edge within open-hand reach; no stepping was needed. Stage the open right index below the visible near-right overhang, then probe upward. Compare lid edges against the fixed rim before following an upward/forward opening path. These are conditional interaction candidates, not a supplied hinge model or reusable absolute trajectory.

In this episode, fresh stereo showed near-edge rise after the small probe and a clear rim gap after the next lift. Short upward/forward translations enlarged the opening. Wrist orientation drifted substantially even when active, changing finger elevation; recompute clearance from actual pose. Observed ankle endpoint drift stayed below 0.3 mm. Final lid opening was under contact; release retention and independent audit were not established. Do not transfer faucet push direction, cube geometry or door trajectories.

After termination submit a complete concise skill_update with lesson, change summary and existing public evidence paths. Preserve failures and prior versions. Respect combined skill-plus-runtime caps. Shared promotion requires cross-task validation and grasp regression; this correction remains task specific.
