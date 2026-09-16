---
name: loco-manip-direct
description: Learn SIMPLE box acquisition and container placement from public evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Grasp the cracker box, lift, transport above the basket rim, lower, release and verify stable container support while standing. Read workspace.json, task_specification, completion_contract, SKILL.md and experience_read. Current contract requires unsupported lift>=.05m held>=.5s and released support>=1s. Native contact alone is nonterminal; final geometry needs host audit.

Use exact workspace Python; install nothing. Only RGB, calibration, named robot state, robot geometry and listed self-experience are allowed. No demonstrations, privileged object/contact state, evaluator/runtime inspection, other simulators or hardware. Act through registered services; host records/exports.

## Retrieve, act, observe

Call loco_start once. Inspect stereo, measured/reference poses, joints, closure and current contract. Before acting, experience_select records sources, applicability, adaptation and rejected transfers; re-select when failures change. Shared437/438 supply retrieve-test-observe-correct. BendPick v6/042–063 supplies an acquisition/lift candidate, not placement competence.

Use latest observation and unique request ID. Reasons state problem, objective, evidence, change, expected observation and errors to avoid. Inspect stereo and both arms/feet after every action. Separate request, execution, contact hypothesis and progress; preserve uncertainty/failures.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active position/orientation; retain inactive components as contracted. Never output q29 or torques. Closure fractions are commands, not aperture/force. Wrist frames are not calibrated TCPs.

Fresh limits override history. Continuous chunks permit2–5 knots,total<=3s; per-knot wrist<=.06m,ankle<=.30m,rotation<=.10rad; total wrist<=.20m,ankle<=.30m,rotation<=.30rad. Active links/gripper goals match throughout; starts/inactive components use measured poses. Single waypoints remain<=.03m/.10rad/.5–3s. Knots are timed references, not arrival waits or a walking primitive.

## Geometry and acquisition

Ray-plane projection is not depth. Triangulate consistent stereo edges using current calibration, reject occluded/textureless matches and high residuals, reproject and relocalize after head/object motion. 
Use native whole-hand meshes, not cube capsules. Vertices include geom-to-body transforms; apply observed body poses. Handle primitive half-sizes/transforms separately. Convex surfaces against an uncertain RGB cuboid can reject interference, not prove contact. Check whole-hand swept clearance against table and basket.

Viewing motions are physical hand motions. Open fingers can displace unseen objects; raised wrists do not establish finger-path clearance. Establish a visible clearance route before yaw/approach; test posture changes incrementally.

Approach open. Require plausible opposing surfaces around the box before staged closure; a thumb wholly above the box is insufficient. Preserve an original pose reference during closure. Verify box-hand co-motion in a10–20mm lift and separate original-target hold before transport. Lift retained box bottom above observed rim, move in bounded increments, lower, release, withdraw and verify support. Closure, target_reached and wrist ascent cannot substitute.

## Control findings and counterexamples

Backend SimpleLiveSim (SIMPLE/MuJoCo), not Isaac. Preserve histories, selections and versions.

Boxplace0001 ended022/native_success during.35 closure;0002 ended003/native_success after3 open-hand arcs. Neither verified acquisition, lift, transport or release; support was ambiguous and successes_so_far=0. Their poses are candidates, not placement recipes; retain original evidence.

Boxplace0003 ended052/episode_step_budget, native_outcome=in_progress, successes_so_far=0. All closures remained0: no verified envelope, acquisition, lift or placement. Configured budget240s; public observations recorded241.92s controlled time and terminal step12096 versus max12000. Preserve this discrepancy without runtime inspection.

003/001 raised both open hands60mm before viewing arcs; these improved visibility without establishing object support.

Centered descent repeatedly steepened attitude and shifted position. Whole-hand checks rejected further descent when palm/proximal interference was predicted.027/028 retraction60mm then rotation improved angular error to.046rad. This does not prove obstacle contact: near-side free-space descent047 and049 also undertracked33/50mm. Do not attribute all stalls to the rim.

Orientation-only041/042 improved angular errors to.091/.038rad but drifted32/35mm;045 drifted48.5mm with.189rad error. Re-localize before reactivating position. Position-only025 did not resolve the stall. Free-right posture affected view and held-left pose; avoid accumulated reference drift.

038 requested both ankles+60mmX; peak X excursion<.15mm, no step.050 common wrist lowering50mm achieved left37mm/right45mm descent but left shifted28mmX. These are diagnostic candidates, not competence. Compare common lowering versus isolated entry only after fresh clearance checks.

## Termination and revision

Await complete responses; reasoning pauses simulation. Timeout is tracking feedback. After three actions finish_attempt may record an evidenced stall and changed hypothesis; follow its next_call and test the change in this episode. No idle budget filling or stopping for slow reasoning.

On rollout_finished stop physical actions immediately. Submit complete evidence-backed skill_update, concise lesson/change_summary and existing evidence paths. Use task_specific; shared promotion needs cross-task validation and grasp regression. Respect831 words/6250 characters and reported non-whitespace cap.
