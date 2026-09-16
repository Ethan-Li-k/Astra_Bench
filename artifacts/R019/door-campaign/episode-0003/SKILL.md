---
name: loco-manip-direct
description: Learn visual G1 SIMPLE manipulation from verified public attempts.
---

# SIMPLE Direct policy

## Objective and boundaries

Use gpt-6-astra/xhigh. Read the complete task in workspace.json. Push the initially closed SIMPLE asset003 door away at least 30 degrees, hold it open at least one simulated second, and remain standing. Use hand contact; never pull the handle or perform the original close-door task. Require ten independent reset successes; other SIMPLE tasks each require one success. Diagnostic replay never counts.

Revise this skill, not weights; no demonstrations. Execute physics only through registered services, never another simulator or real robot. Existing environments/runtime remain read-only. Inspect only campaign public evidence, robot geometry and explicitly listed transferred_self_experience. Never inspect hidden object, hinge, contact, evaluator state or unlisted experiments. Use workspace.json's exact Python; install nothing. Evidence is read-only; new outputs belong under the allowed rollout root.

## Observe, review, execute

Read workspace.json, canonical SKILL.md and experience_read. Retrieve memory versions and cited public rollouts selectively. Adapt candidates to fresh RGB and named state; never replay blindly. Controller profiles can differ between episodes: revalidate response.

Call loco_start once with the supplied directory. Inspect head stereo RGB, calibration, measured/reference poses, named joints and closure. No table plane, object dimensions or calibrated hand TCP are supplied.

Review one bounded waypoint from the latest observation. Use its fresh path/ID, a unique scalebfm_act request ID and an evidence-based reason. Follow returned next_call paths, including geometry calls. Await complete responses. After every action inspect fresh RGB and actual poses. Separate reference changes, tracking, contact hypotheses and task progress. Change direction, clearance, orientation, step size, duration or closure after failure; never repeat unchanged failures.

Continue until rollout_finished=true. After at least three executed actions, an evidenced stall can be ended with finish_attempt and a changed hypothesis instead of repeated idle holds. This is failure, not success. Submit skill_update after the host confirms termination; the host continues the campaign.

## Four-point contract

Map by name in public order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Never copy joint arrays positionally or output q29, torques or open-loop task scripts.

Include all four absolute position_world_m and unit quaternion_wxyz poses. Declare active.position and active.orientation. Inactive components retain references, even when geometry tools return measured poses. Measured quaternions alone do not activate tracking. Active targets stay within 0.03 m and 0.10 rad of current measurement; duration 0.5-3 s. Feet normally retain support. ScaleBFM/native SIMPLE PD run at 50/200 Hz; physical budget is 240 s, paused during reasoning.

Grippers are ramped closure fractions, 0=open and 1=closed. Empty active lists allow gripper-only phases, not contact detection. SIMPLE hand collisions differ from prior capsule hands. Infer clearance from current images and poses; import no foreign TCP offsets, closure settings or object coordinates.

Geometry tools calculate without executing: translate uses world XYZ metres; rotate uses world axis-angle radians and a pivot; place_local_point requires an explicitly declared link-local point.

## Perception and verification

Ray-plane projection is not depth. Derive focal length from calibrated height and vertical FOV. Use reliable stereo correspondences; reject shadows, occlusion intersections and inconsistent edges. Infer door surface, frame and free space from RGB.

Establish actual approach before long arm extension. Verify ankle advance and body clearance; wrist motion or camera lean alone is not walking. Establish gentle hand contact, test a small push and compare door motion with its frame. Relocalize after slip. Closure, overlapping pixels or target_reached do not prove contact/opening. Verify opening, physical dwell and standing separately from native success.

## Tested experience

Transferred grasp v14/437/438 informs procedure, not door geometry or universal recovery.

R019/0001 exhausted its budget without approach. Feet barely advanced; repeated measured-position targets accompanied about 0.60/0.55 m wrist upward drift. Stop reanchoring biased measurements. Compare residuals with original references and bounds; activate original targets only when still within bounds. Left local-X rolls tracked with positions retained, but subsequent descent failed.

R019/0002 used checkpoint body PD. Lift-forward, all-four +20 mm X, and toe-up lift probes all timed out without ankle advance. The common translation briefly tracked wrists within 2.6 mm; this was arm response, not walking. Retained wrist residuals later rose to about 20-22 mm. Original ankle support recovery reached target. The attempt ended as policy_declared_stall after four actions, without verified contact/opening. Do not repeat these probes unchanged or extrapolate transient wrist tracking.

Next hypothesis, unverified: test bounded lateral load transfer with an isolated ankle-roll candidate and retained positions before attempting swing. Require measured body response and support clearance; do not assume unloading from a command.

## Audit and learning

Separate construction errors, explicit service errors, tracking timeouts and uncertain transport. Preserve exact errors and layers. Consult public receipts and experience_read before retries; never replay uncertain or terminal actions. Explicit terminal wrappers override raw next_call/native outcome.

After termination, read public receipts/trajectory and submit a complete revised skill, concise lesson and exact existing evidence files through skill_update. Evidence must be inside this episode's public rollout; agent RPC receipts are not accepted. Check all length caps and retain versioned evidence. Keep learning separate from frozen evaluation.
