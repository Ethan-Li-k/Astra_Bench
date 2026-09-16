---
name: loco-manip-direct
description: Learn native SIMPLE box acquisition and container placement from public evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Find the cracker box and basket, grasp, lift, transport above the rim, lower, release and verify stable container support while standing. Native box-container contact success alone does not establish this sequence or inside-container placement.

Read workspace.json, task_specification, SKILL.md and experience_read. Use exact workspace Python; install nothing. Only RGB, calibration, named robot state, robot geometry and listed self-experience are allowed. No human demonstrations, privileged object/contact state, evaluator/runtime inspection, other simulators or hardware. Act through registered services; host records/exports.

## Retrieve, act, observe

Call loco_start once. Inspect stereo, measured/reference poses, joints, closure and current action contract. Before acting, experience_select records sources, applicability, adaptation and rejected transfers; re-select on changed failures. Shared437/438 supply retrieve-test-observe-correct. BendPick v6/042–063 supplies a self-generated acquisition/lift candidate, not placement competence.

Use latest observation and unique request ID. Reasons record problem, objective, evidence, change, expected observation and errors to avoid. After every action inspect stereo and measured tracking of both arms and feet. Separate request, execution, contact hypothesis and task progress. Preserve uncertainty and failed tests.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active position/orientation; retain inactive components as contracted. Never output q29 or torques. Closure fractions are commands, not aperture/force. Wrist frames are not calibrated TCPs.

Current episodes enabled continuous chunks:2–5 knots,total<=3s; per-knot wrist<=.06m,ankle<=.30m,rotation<=.10rad; total wrist<=.20m,ankle<=.30m,rotation<=.30rad. Active links/gripper goals match throughout; starts/inactive components use measured poses. Single waypoints remain<=.03m/.10rad/.5–3s. Read fresh limits. Knots are timed references, not arrival waits or a walking primitive.

## Geometry and verification

Ray-plane projection is not depth. Triangulate consistent stereo edges using current calibration; reject occluded/textureless matches and high residuals. Reproject estimates and relocalize after displacement or head motion.

Use native whole-hand meshes, not cube capsules. Vertices already include geom-to-body transforms; apply observed body poses. Handle primitive half-sizes/transforms separately. Convex surfaces versus an RGB cuboid can reject interference, but approximate fits/bounds do not prove contact. Check whole paths, uncertainty, table and container clearance.

Viewing motions are physical hand motions. Open fingers can displace an unseen box or strike the basket. A raised wrist endpoint does not establish swept-finger clearance. When targets are occluded, first establish a visible clearance route before further yaw/approach; test posture changes in bounded increments. Do not blindly replay the upper-body arc candidate.

Approach open; require plausible opposing surfaces around the box before staged closure. Preserve an original pose reference during closure rather than accumulate drift. Verify box-hand co-motion in a short lift and separate original-target hold before transport. Lift retained box bottom above observed rim, move in bounded increments, lower, release, withdraw and verify container support. Closure, target_reached and wrist ascent cannot substitute for these observations.

## Task evidence and counterexamples

Backend SimpleLiveSim (SIMPLE/MuJoCo), not Isaac. Keep original histories, selections and versions.

Boxplace0001 ended at022/native_success after22 actions/~94.94 controlled seconds during staged .35 closure. No lift, retained transport, release or stable placement was demonstrated. Final box appeared adjacent to basket.001 yaw/002 timed foot lift did not establish stepping.003–005 hand arcs improved view; attitude/descent coupled and free-arm drift degraded visibility.015 free-right-wrist lowering improved view.017–019 mesh/visual checks supported a candidate;020–022 retained019 pose through staged closure. These are counterexamples/candidates, not a completed placement recipe.

Boxplace0002 ended at003/native_success after3 actions/15.02 controlled seconds (sim_s20.025), both closures0 throughout. Three measured .27rad hand arcs improved view;003 added45mm rise.002 left position error47mm;003 left tracked within.5mm, but right angular error.241rad. Final ankles stayed near initial support (<.2mm endpoint displacement). Stereo showed box-like cuboid adjacent to/overlapping the basket and left hand; support/contact remained ambiguous. Acquisition, retained lift, transport and release were never verified. Even open-hand viewing can precede native termination; do not infer a harmless camera-only adjustment or promote placement success. Terminal receipt still reported successes_so_far=0; host audits geometry separately.

## Termination and revision

Await complete responses; simulation pauses during reasoning. Timeout is tracking feedback, not automatic failure. After three actions finish_attempt may record an evidenced stall and changed hypothesis; follow its next_call and test that change in the same episode. No idle budget filling or stopping for slow reasoning.

On rollout_finished stop physical actions immediately. Submit complete evidence-backed skill_update with concise lesson/change_summary, preserving sources, versions and failures. Keep within831 words/6250 characters and reported non-whitespace cap. Use task_specific; shared promotion requires cross-task validation and grasp regression.
