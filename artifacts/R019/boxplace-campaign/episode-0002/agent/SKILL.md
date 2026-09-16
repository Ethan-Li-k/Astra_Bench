---
name: loco-manip-direct
description: Learn native SIMPLE box acquisition and container placement from public evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Find the cracker box and basket, grasp, lift, transport above the rim, lower, release and verify stable container support while standing. Native box-container contact success alone does not establish this sequence or inside-container placement.

Read workspace.json, task_specification, SKILL.md and experience_read. Use the exact workspace Python; install nothing. Only RGB, calibration, named robot state, robot geometry and listed self-experience are allowed. No human demonstration, privileged object/contact state, evaluator/runtime inspection, other simulators or hardware. Act through registered services. Host records/exports.

## Retrieve, act, observe

Call loco_start once. Inspect current stereo, measured/reference poses, joints, closure and action contract. Before acting, experience_select records sources, applicability, adaptation and rejected transfers; re-select on changed failure modes. Shared437/438 supply retrieve-test-observe-correct. BendPick v6/042–063 supplies a self-generated acquisition/lift candidate, not placement competence.

Use latest observation and unique request ID. Reasons record problem, objective, evidence, change and expected observation. After every action inspect RGB and measured tracking. Separate request, execution, contact hypothesis and task progress. Preserve uncertainties and failed tests.

Include all four absolute world positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active position/orientation; retain inactive references as specified. Never output q29 or torques. Closure fractions are commands, not aperture/force. Wrist frames are not calibrated TCPs.

Read current limits: this episode allowed single waypoints within0.03m/0.10rad/0.5–3s. Enabled continuous chunks allowed2–5 knots, total<=3s, per-knot wrist<=0.06m/ankle<=0.30m/rotation<=0.10rad; total wrist<=0.20m/ankle<=0.30m/rotation<=0.30rad. Active links and gripper goals must match throughout; chunk starts/inactive components use measured poses. Knots are timed references, not arrival waits or a walking primitive.

## Geometry and verification

Ray-plane projection is not depth. Triangulate consistent stereo edges with current calibration; reject occluded/textureless matches and high residuals. Head motion changes pixels. Reproject estimates and relocalize after displacement.

Use native whole-hand meshes, not cube capsules. Vertices already include geom-to-body transforms; apply observed body poses. Handle primitive half-sizes/transforms separately. Full convex surfaces versus an RGB cuboid can reject interference, but approximate fits and conservative bounds do not prove contact. Check entire paths, uncertainty and container rim clearance.

Approach open; require plausible opposing surfaces around the box before staged closure. Preserve an original pose reference during closure rather than accumulate drift. Verify box-hand co-motion in a short lift and separate original-target hold before transport. Lift the retained box bottom above the observed rim, move in bounded increments, lower, release, withdraw and verify container support. Closure, target_reached and wrist ascent cannot substitute for these observations.

## Task-specific evidence: boxplace0001

Backend SimpleLiveSim (SIMPLE/MuJoCo), not Isaac. Episode terminated at022 with native_success after22 actions/~94.94s of controlled physics (sim_s99.945). No lift, retained transport, release or stable placement was demonstrated. Final RGB shows the box adjacent to the basket with the hand nearby. Do not promote this as a completed placement skill; host audits geometry separately.

Initial view faced away from the table.001 coordinated yaw and002 timed80mm left-foot lift produced negligible ankle movement; neither proves a step.003–005 upper-body hand arcs revealed the table while feet stayed supported. This is a viewing candidate, not locomotion.

006–012 prepared the open left hand. Attitude corrections/descent coupled strongly: requested rpy[1.30,.89,-.38] became approximately[1.51,1.01,-.09]. Repeatedly anchoring an inactive free wrist allowed accumulated drift and worsened visibility.012 stall report did not terminate;013 changed posture coupling.015 lowering the free right wrist beside the table improved the view markedly; actual descent was~94mm for120mm requested. Active right targets still undertracked, so inspect both arms.

Current stereo supported box near x[-.397,-.337],y[-.127,.033],top.6155m and basket rim around.54m; these are uncertain episode-only visual estimates, not reset coordinates. High-residual corner matches were rejected. Native convex checks guided017–019 medial entry and rejected a down/medial candidate without forward clearance. Requested small medial corrections sometimes barely moved; avoid unchanged retries.

019 open wrist was[-.3857,.0174,.7349], achieved rpy[1.403,1.076,-.249].020–022 retained019's pose reference and closed.15,.25,.35. At022 native termination occurred during closure, before the planned lift probe. These values are evidence, not a grasp recipe. A contact-based native trigger can precede the intended task sequence.

## Termination and revision

Await complete model/service responses; simulation pauses during reasoning. A timeout is tracking feedback, not automatic episode failure. After three actions finish_attempt may record an evidenced stall and changed hypothesis; follow its next_call and test the change in the same episode. No idle budget filling or stopping for slow reasoning.

On rollout_finished stop physical actions immediately. Submit complete skill_update with concise lesson/change_summary and existing public evidence, preserving versions/failures/source selections. Keep within831 words/6250 characters. Use task_specific; shared promotion requires cross-task validation and grasp regression.
