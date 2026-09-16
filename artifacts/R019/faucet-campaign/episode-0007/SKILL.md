---
name: loco-manip-direct
description: Learn native faucet operation through public visual evidence.
---

## Control and evidence

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, assembled SKILL.md and experience_read. Preserve the native task. Use only campaign public evidence, named robot state, calibration, robot geometry and listed transferred_self_experience. No demonstrations, privileged state, runtime inspection, other simulators or hardware. Use the workspace interpreter; install nothing.

Call loco_start once; never during terminal review. Inspect both RGB views, calibration, measured/reference poses, joints, commanded closure and current finger bounds. Before acting, experience_select records sources, rationale, adaptation and rejected reuse; reselect on changed failure mode. Record question, goal, forbidden repeats and uncertainty. Transfer grasp437/438's retrieve-test-observe-correct procedure, never coordinates, geometry, plane, closure or orientation. Grasp success proves no faucet/locomotion transfer.

Review actions from fresh evidence with unique ID, purpose and expected visible change. Include all four absolute world poses in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation. Single waypoints retain inactive references and obey current per-link limits,0.10rad rotation and0.5–3s duration. Never output q29 or torques. Geometry tools calculate; scalebfm_act executes. Closure fractions are ramped commands:0 open,1 closed; neither force nor aperture. Wrists are not calibrated TCPs.

When enabled, continuous chunks have2–5 knots, each0.5–3s,total≤3s; segment wrist/ankle translation≤0.06/0.30m, from measured start≤0.20/0.30m; rotation≤0.10rad/segment,≤0.30rad/chunk. Start/inactive components use measured poses; active sets/gripper goals stay constant. No intermediate arrival waits. Revalidate current contract; no gait is supplied.

Inspect fresh stereo/achieved poses after actions and traces/peak ankles after chunks. Separate target, tracking, contact hypothesis and progress. Arrival, timeout, ankle rise, unequal finger joints, closure or overlap proves neither walking, grasp nor lever motion. Change a justified variable after failure; avoid unchanged retries and biased anchors. Await complete responses; reasoning pauses physics.

Triangulate reliable calibrated correspondences; verify reprojections. Epipolar fit proves neither correspondence nor control identity; ray-plane projection is not depth. Reject shadows, occlusions and mismatched endpoints. Transform current finger bounds with actual attitude and inspect whole-hand collision geometry. Verify enclosure before contact closure and retention independently. After two unverified motion probes, withdraw/reveal and revise.

Monitor both feet even when inactive. Material unintended support motion requires withdrawal/reassessment. Measured support holds are hypotheses, not stability guarantees. Cancel unachieved foot references; never command stale anchors beyond limits. Check touchdown, yaw drift and opposite support after partial excursions.

Continue until rollout_finished, native termination, safety/system fault or budget end. finish_attempt records an evidenced stall and changed hypothesis; it does NOT terminate physics. Follow its returned observation with a changed safe test. Do not idle or stop for reasoning delay. rollout_finished overrides raw in_progress/next_call.

After no_execution, correct with fresh ID/directory only if usable. Runtime-stopped/motion-active faults require host recovery evidence, not command variants. Never replay uncertain execution. After termination submit complete skill, lesson/change_summary and existing public evidence within caps. Preserve versions/failures; shared promotion requires cross-task validation/grasp regression.

## Faucet evidence and candidates

Goal: control angle magnitude>0.7rad plus native accumulation while stable; host determines success. No door-style one-second criterion. Report visible retention separately.

Versions1–4 preserve earlier failures:0001 exhausted74 actions without verified grasp/opening; side approaches, rolls and closure.20–.50 failed.0003 low insertion displaced feet108/83mm: do not repeat.0004 high-thumb misses17/26mm and no-motion distal probes; thumb-up rolls proved clearance only.0005 ended backend_execution_error after one yaw chunk; sidestep/recovery never executed. Host reported duration repair.

Episode0006:64 actions/241.10s,25 reached/39 timed out; episode_step_budget,12055/12000 steps,zero successes,SimpleLiveSim (not Isaac). Stalls were nonterminal. Broad plate versus rear protrusion identity remained unresolved. Opposite-side distal probes, front-edge closure.48, lift and world-X/Y/Z tests established no lever motion or retention. No persistent change verified after withdrawal; do not promote guessed pivots.

Local-X rolls21–23 and31–34 tracked about0.009–0.029rad; global pitch often missed0.14–0.26rad. Front retract-then-lower43 recovered tracking after blocked descents41/42; this establishes clearance only.

Locomotion response is conditional: right lateral tests1/28 and forward tests57/58 produced negligible swing. Left forward/side test56 moved64/42mm, peak rise24.75mm, yaw miss0.109rad. In changed stance, right test59 with135mm leftward wrist shift moved91/17mm, peak rise20.59mm, yaw miss0.119rad; left support moved<0.36mm. Neither full-foot clearance, reliable gait nor amplitude causality is verified. Retrieve56–59's public references/traces; adapt stance, clearance and support.

After59, measured support stayed near achieved poses; farther rear approach62 tracked2.8mm. Stance benefit remains a hypothesis. Final rear-thumb probe63 tracked but showed no verified control response;64 reopened/withdrew at budget end.

Next: assess conditional stepping earlier, obtain a clear side connection and distinguish control identity before repeated contact.
