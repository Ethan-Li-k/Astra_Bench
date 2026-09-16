---
name: loco-manip-direct
description: G1 UMI-4 visual control with task-local oven-opening evidence.
---

## Start and select

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, this skill and experience_read. Current objective and observed contract override history. Use only allowed public self-experience, RGB, calibration and named robot geometry/state; no demonstrations, hidden object/contact state, evaluator inspection or other simulators. Use the workspace interpreter.

Call loco_start once. Inspect stereo, measured/reference poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptation and exclusions; reselect when the failure mode changes. Retrieve relevant versions and cited actions selectively. Record problem, goal, errors and next test in public reasons/notes.

## Execute and observe

Use latest observation and unique request ID. State evidence, purpose and predicted observable change. Supply all four named wrist/ankle poses in world metres and unit wxyz; declare active position/orientation. Inactive components follow the current contract. Never output joints or torques. Grippers ramp 0=open, 1=closed; neither closure nor a wrist frame is calibrated contact/TCP information.

Use reported single-waypoint limits. Continuous chunks require explicit enablement; respect segment and total bounds. After each action inspect fresh stereo and actual poses. Ankle rise alone proves neither sole clearance nor stable gait. Separate target, tracking, contact hypothesis and progress. Change a justified variable after failure; do not accumulate biased anchors.

Use render_intrinsics and pixel centers. Ray-plane projection is not depth. Reject ambiguous stereo correspondence, shadows and occlusion; refine depth from identifiable features. Check whole-hand clearance using current robot mesh geometry. Pixel overlap and hand displacement cannot prove coupling. Establish grasp enclosure before closure, or explicitly test an open-hand interaction. Verify the moving panel against fixed housing.

Await complete inference and action responses; simulation pauses during reasoning. Continue until rollout_finished, actual safety/system termination or budget end. Tracking timeout is not task failure. finish_attempt records a nonterminal stall and changed hypothesis; test that hypothesis in the same episode. Do not use idle holds to exhaust budget.

## Oven-specific candidate: episode0001

Native SIMPLE success after14 actions/53.44 physical seconds; final stereo shows upper door open with exposed interior and level ankles. Backend SimpleLiveSim/MuJoCo, not Isaac. Independent supervisor audit and deliberate release retention remain separate.

Retrieve episode0001 public history, especially actions5-14. Actions1-5 adapted door16 unloaded alternating forward/apex/landing references with low open wrists; actual foot advance differed from requests. Revalidate support drift and reach; this is not a general gait or loaded-walking result.

Stationary right-hand staging raised the hand, rolled its opposition across the upper bar, then lowered/advanced while open. Orientation requests were only partially achieved; wrist roll approached1.98rad. Use achieved geometry, not requested orientation. Initial coarse stereo height estimates were revised by patch correspondence. Action12 forward50/down30mm achieved only15/down9mm: obstruction versus reach limit remained uncertain.

Action13 open-hand backward25/down8mm probe visibly separated upper panel from fixed housing. Action14 backward25/down12mm increased opening to native terminal. The observed path was outward/downward; do not assume it from household hinge conventions. No gripper closure was used. This supports an open-finger hooking candidate, not a proven handle grasp. Preserve misses; never replay coordinates.

## Revision

After termination submit complete skill_update with lesson, change summary, scope and evidence paths. Preserve old versions and failures. Keep skill plus runtime within all reported caps. Shared promotion requires supervisor validation across tasks and grasp regression; this oven procedure remains task_specific.
