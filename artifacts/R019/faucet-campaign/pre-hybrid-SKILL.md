---
name: loco-manip-direct
description: Learn native SIMPLE manipulation from visual attempts.
---

# SIMPLE Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. Read the complete task in workspace.json and preserve its native success criterion. Require at least one independent reset success for that task and remain stable. Diagnostic replay is not a policy trial.

Revise this skill, not weights; no demonstrations. Physics uses registered services only, never a second simulator or real robot. Existing environments/runtime and evidence remain read-only. Inspect only campaign public evidence, named robot state, camera calibration, robot geometry and explicitly listed transferred_self_experience. Never inspect object/contact truth, hidden state, evaluator internals or unlisted experiments. New outputs belong under the allowed rollout root. Use the exact workspace Python; install nothing.

Read workspace.json, canonical SKILL.md and experience_read. Retrieve successful procedures and relevant failures selectively from allowed memory/versions and cited rollouts. Compare current RGB/state before adapting candidates; never blindly replay. Ten grasp successes transfer an observe-test-correct procedure, not cube coordinates or hand geometry.

## Observation and action

Call loco_start once at the supplied path. Inspect both head views, calibration, named measured/reference poses, joints and closure. No object dimensions or table plane are supplied. Independent resets retain learned skill.

Review one bounded waypoint per call using the latest observation, a unique request ID and evidence-based reason. Follow next_call paths, including geometry results. Await complete responses. After every action compare actual wrist displacement, attitude, feet and fresh RGB. Distinguish tracking, object motion, failure and hypothesis. A target, timeout, closure or occlusion proves neither grasp nor impossibility.

Continue until rollout_finished=true. After a failed test change direction, clearance, attitude, step size, duration or closure; never repeat unchanged failure. After two contact tests without identifiable object motion, withdraw and revise the contact model before spending more budget on nearby variants.

## Four-point contract

Map by name in public order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Never copy joint arrays positionally or output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation; inactive components retain reference. Measured quaternions alone do not activate orientation tracking. Each target stays within 0.03 m and 0.10 rad of current measurement; duration 0.5-3 s. ScaleBFM/native SIMPLE PD run at 50/200 Hz. Physical budget is 240 s; reasoning pauses physics. Read remaining_steps because settling/timeouts consume additional execution.

Grippers are ramped closure fractions, 0=open and 1=closed. Empty active lists allow gripper-only phases, not contact sensing. Wrist links are not calibrated TCPs. Infer current finger clearance from stereo and measured poses; import no capsule geometry or foreign offsets.

four_point_translate uses world XYZ metres. four_point_rotate uses world axis-angle radians and a pivot. four_point_place_local_point requires an explicit link-local point. Geometry tools calculate, never execute.

## Visual contact and support

Derive focal length from calibrated image height and vertical FOV. Ray-plane projection is not depth. Triangulate reliable corresponding edges and verify reprojections; reject shadows, occlusion and inconsistent matches. Image vertical position is not world height. Relocalize after camera motion. Enlarge ambiguous RGB regions before contact decisions.

Distinguish moving component and fixed body. Hinge axis and contact surface remain hypotheses until a small test produces consistent relative motion. For the faucet, confirm actual lever rotation beyond 40 degrees in either permitted direction and the host outcome. Wrist rotation is not lever rotation.

Monitor feet even when inactive. Uncommanded displacement is a stability warning, not walking evidence. Release constrained contact and stabilize before continuing. Zero-displacement targets at measured support positions may help; never command arbitrary foot translations or assume attitude remains fixed.

Original-target holds sometimes recover undertracking but failed in faucet action10. Do not accumulate attitude drift by reanchoring blindly. Isolated rotation or separating translation from attitude can recover tracking; verify each instance. Closure increases require separate motion verification.

## Faucet episode0001 evidence

74 actions exhausted the budget with zero successes. The terminal wrapper reported episode_step_budget despite raw native_outcome=in_progress. No verified lever rotation or grasp was established; moving-part identity, pivot and contact geometry remained uncertain.

Early high approach and constrained contact produced repeated attitude timeouts and foot drift (actions23/26). Later measured foot-position holds accompanied steadier support, without proving causality. Side withdrawal30 and forward approaches31/44/45 tracked well; local-X rolls54-59 also tracked. These are tracking candidates, not an opening procedure. Closures .20-.50 and motion tests established no grasp or lever progress. Recheck public RGB before reuse. Final74 showed an open withdrawn hand.

## Audit and learning

Separate local analysis errors, explicit service errors, tracking timeouts and uncertain transport. Preserve exact errors and layers. Read receipts/experience before retries; never replay uncertain or terminal actions. Explicit terminal wrappers override generic next_call text.

After success, budget end or fault, read receipts/trajectory and submit the complete revised skill, concise lesson and existing public rollout files through skill_update. Check all word, character and non-whitespace caps. Keep skill learning separate from frozen evaluation.
