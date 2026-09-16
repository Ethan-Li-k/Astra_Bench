---
name: loco-manip-direct
description: Learn native faucet operation through public visual evidence.
---

## Control and evidence

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Preserve the native task. Use only campaign public evidence, named robot state, calibration, robot geometry and listed transferred_self_experience. No human demonstrations, hidden object/contact/evaluator state, runtime inspection, other simulators or hardware. Use the workspace interpreter; install nothing.

Call loco_start once; never in terminal review. Inspect both RGB views, calibration, measured/reference poses, joints, commanded closure and current finger bounds. Before acting, experience_select records source IDs, rationale, adaptation and rejected reuse; reselect on changed failure mode. Record question, goal, forbidden repeats and uncertainty. Transfer grasp437/438's retrieve-test-observe-correct procedure, never coordinates, geometry, closure, plane or orientation. Grasp success does not establish locomotion/faucet transfer.

Review each action from fresh evidence with unique request ID, purpose and expected visible change. Include all four absolute world poses in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation. Single waypoints retain inactive references and obey current per-link limits, 0.10rad rotation and 0.5–3s duration. Never output q29 or torques. Geometry tools calculate; scalebfm_act executes. Closure fractions are ramped commands: zero open, one closed; neither force nor aperture. Wrists are not calibrated TCPs.

Enabled continuous_chunk_contract: 2–5 knots, each0.5–3s, total≤3s; segment wrist/ankle translation≤0.06/0.30m, from measured start≤0.20/0.30m; rotation≤0.10rad/segment,≤0.30rad/chunk. Start/inactive components use measured poses; active sets/gripper goals stay constant. Knots have no arrival waits. Revalidate current bounds; no gait is supplied.

After blocking actions inspect fresh stereo and actual poses; for chunks inspect motion traces/peak ankles. Separate requested target, tracking, contact hypothesis and task progress. Timeout, arrival, ankle rise, closure or overlap proves neither walking, grasp nor lever motion. After failure change a justified variable; avoid unchanged retries and biased anchors. Await complete service/model responses; reasoning pauses physics.

Triangulate reliable correspondences with calibrated conventions and verify reprojections. Epipolar agreement does not prove correspondence or moving-part identity; ray-plane projection is not depth. Reject shadows, occlusions and mismatched endpoints. Transform current finger bounds with actual attitude; overlap is not contact. Check whole-hand clearance using robot-only geometry. Test contact/pivot with a short probe and independent observation; preserve disagreement between views.

Monitor feet even when inactive. Material uncommanded displacement requires withdrawal/reassessment. Measured support holds are hypotheses, not stability guarantees; never command stale anchors beyond limits. Stop physics on rollout_finished despite raw in_progress or generic next_call. After three actions, finish_attempt may end an evidenced stall; this is not success. Avoid idle holds.

After no_execution, correct with fresh ID/directory only if service is usable. Runtime-stopped/motion-active errors require host recovery evidence, not more command variants. Never replay uncertain execution or equate a resumed model turn with recovery. After termination submit complete local skill, lesson/change_summary and existing episode public evidence within caps. Preserve versions/failures; shared promotion requires cross-task validation and grasp regression.

## Faucet evidence

Goal: move the small water-control lever beyond0.7rad and satisfy native accumulation while stable. Host outcome determines success; no door-style one-second criterion. Report visible retention separately.

Episode0001 exhausted74 actions without verified grasp/opening; side approaches, local-X rolls and closure.20–.50 failed; constrained approaches slipped support.

Episode0003:14 actions, no success. Action8 position error<2mm but attitude error0.279rad. Broad plate identity unverified; probes10/11 showed no motion. Lower insertion13 displaced feet108/83mm; withdrawal14 restored steady feet. Do not repeat insertion.

Episode0004 stalled after35 actions, no success; feet stayed within0.733mm. All-point lateral25mm failed to establish an oblique view or step. High thumb route18/19 missed17/26mm; do not accumulate it. Rear-feature identity remains unverified; coordinates do not transfer. Closure.20 changed the envelope only. Thumb-up rolls27–29 tracked; clearance candidate only. Lower31/lateral32 showed no response;32 moved2.7mm, missed14.3mm. Withdrawal33–35/reopening: no retention verified, right partly occluded.

Episode0005:backend_execution_error, one confirmed yaw chunk/4.4 physical seconds; success=false; rollout_finished=true overrides raw in_progress. Two1.2s knots requested yaw−0.09/−0.18rad; timed_out. Wrist position errors10.35/29.48mm; ankle motion0.255/0.131mm, attitude miss≈0.179rad. Left camera moved[-4.557,38.696,1.064]mm and rotated≈0.101rad; view changed but control identity remained unresolved. No gait, contact, opening or retention verified.

Host execution_error: legal3s gripper ramp exceeded3s through floating-point subtraction; admission blocked later requests without physical execution. Sidestep and recovery requests are unexecuted, not failed physical tests. Host reports repair for future resets.

Next: obtain an unobstructed oblique view of the stem connection; coordinated sidestep remains untested. Reassess poses, support and view before approaching. Consider opposite-side distal-finger contact with one camera clear. Establish visible relative motion and pivot before continuing rotation. After two no-motion tests, withdraw and revise.
