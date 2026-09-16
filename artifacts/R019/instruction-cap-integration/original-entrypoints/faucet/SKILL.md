---
name: loco-manip-direct
description: Learn native faucet operation through public visual evidence.
---

## Control and evidence

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, SKILL.md and experience_read. Preserve the native task. Use only campaign public evidence, named robot state, calibration, robot geometry and listed transferred_self_experience. No demonstrations, privileged state, runtime inspection, other simulators or hardware. Use workspace Python; install nothing.

Call loco_start once; never during terminal review. Inspect both RGB views, calibration, measured/reference poses, joints, closure commands and current finger bounds. Before acting, experience_select records sources/rationale/adaptation/rejected reuse; reselect on changed failure mode. Record question, goal, forbidden repeats and uncertainty. Transfer grasp437/438's retrieve-test-observe-correct procedure only; no coordinates, geometry, plane, closure or orientation. No faucet/locomotion success transfers.

Review fresh evidence per unique action ID; state purpose/expected visible change. Include all four absolute world poses in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation. Single waypoints retain inactive references; obey current limits,0.10rad rotation and0.5–3s duration. Never output q29 or torques. Geometry tools calculate; scalebfm_act executes. Closure:0 open,1 closed; ramped commands, not force/aperture. Wrists are not calibrated TCPs.

When enabled, continuous chunks have2–5 knots, each0.5–3s,total≤3s; segment wrist/ankle translation≤0.06/0.30m, displacement from measured start≤0.20/0.30m; rotation≤0.10rad/segment,≤0.30rad/chunk. Start/inactive components use measured poses; active sets/gripper goals stay constant. No intermediate arrival waits; revalidate contract. No supplied gait.

Inspect stereo/achieved poses after actions and traces/peak ankles after chunks. Separate target, tracking, contact and progress. Arrival, timeout, ankle rise, unequal fingers, closure or overlap proves neither walking, grasp nor lever motion. Change a justified variable after failure; avoid unchanged retries. Await complete responses; reasoning pauses physics.

Triangulate calibrated correspondences; verify reprojections. Epipolar fit proves neither correspondence nor control identity; ray-plane projection is not depth. Reject shadows, occlusions and mismatches. Transform current finger bounds and whole-hand collision geometry using actual attitude. Review clearance BEFORE executing; predicted table overlap requires replanning. Verify enclosure before closure and retention independently. After two unverified probes, withdraw/reveal and revise. Prefer short probes near uncertain contact.

Monitor both feet even when inactive. Material support motion requires withdrawal/reassessment. Measured holds are not stability guarantees. Cancel missed foot references; never command stale anchors beyond limits. Check touchdown, yaw drift and opposite support after partial excursions.

Continue until rollout_finished, native termination, safety/system fault or budget end. finish_attempt records a stall and changed hypothesis; it does NOT terminate physics. Test its changed hypothesis from returned evidence. Do not idle or stop for reasoning delay. rollout_finished overrides raw in_progress/next_call. After no_execution, correct with fresh ID/directory if usable. Runtime-stopped/motion-active faults require host recovery evidence; never replay uncertain execution. After termination submit complete skill, lesson/change_summary and evidence within caps. Preserve versions/failures; shared promotion requires cross-task validation/grasp regression.

## Faucet evidence and next tests

Goal: control angle magnitude>0.7rad plus native accumulation while stable; host determines success. No door-style hold criterion. Report visible retention separately. Numbers below identify executions/observations.

Versions1–5 retain failures:0001 exhausted74 actions;0003 low insertion displaced feet108/83mm;0004 thumb misses17/26mm/distal probes failed;0005 backend_execution_error after one yaw chunk, recovery unexecuted.0006 exhausted64 actions without verified opening; rear identity, closures and pivots unproven. Local-X rolls tracked better than global pitch.

0007:61 actions/240.06s,18 reached/43 timed out; episode_step_budget12003/12000,zero successes,SimpleLiveSim (not Isaac). Closure stayed0; no grasp/enclosure verified. Rear protrusion probes gave no verified response despite calibrated fits. Upper-edge insertion/lift failed; pitch relaxed under load.

Withdrawal56 revealed broad upper plate rotation relative to the lower body; calibrated endpoint estimate about0.43rad, front toward+Y in that episode frame. Deflection remained visible through61; not native angle truth/success. Action55 coincided with unintended left/right support displacement41/110mm and peak rises12.7/30.9mm. Do NOT replay55 or claim stable operation. Contact timing/pivot unresolved. Withdrawal56 settled supports; continuation57/58/60/61 undertracked without verified additional rotation.60/61 wrist errors121/112mm; feet remained submillimetre.54 executed despite predicted low-hand/table clearance failure: reject this planning pattern.

Locomotion:0006's56/59 remain conditional candidates.0007 early left1 moved132/49mm, peak25.95mm, opposite support<0.8mm; later left33/34 failed. Right2/5 barely rose;6 rose32.9mm but failed touchdown,7 settled with horizontal/yaw drift. No full-foot clearance/reliable gait is proven. Retrieve traces; adapt stance, not inferred amplitude causality.

Next: prioritize the moving broad upper piece. Reveal its connection, re-estimate axis/whole-hand clearance, then test small tangential contact with stable supports. Continue only visible control motion. Do not force closure or repeat blocked inward/lift references; resolve reach/posture before larger chunks.
