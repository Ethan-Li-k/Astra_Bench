---
name: loco-manip-direct
description: Learn G1 floor-cube pickup, walking and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh through the authorized second-account launcher; no fallback. Read workspace.json, task_specification, SKILL.md, experience_read and required user update. Goal: walk, grasp floor cube, carry airborne, release inside original wooden tabletop, withdraw hands and stand. Old tabletop success cannot count.

Before decisions record problem, goal and mistakes to avoid in reason/NOTES.md. Call experience_select before acting and when failure mode changes. Select shared_core verification, own_tabletop_grasp_skill geometry and task_skill failures; revalidate. Only listed public evidence, RGB, calibration and named robot proprioception are allowed. No simulator internals, host audits, hidden state, supervisor notes or other campaigns. Registered services alone execute physics; no qpos writes, forces, attachment, fixed base, alternate tracker, gain/mode changes or hardware.

Call loco_start once. Preserve/inspect initial head/wrist RGB; locate cube and table. Project z=0 only for visible floor points, never raised corners. Derive focal length from image height/vertical FOV; reject shadows and inconsistent reprojections. Check both views where visible. World robot poses are simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all world metre positions and unit wxyz quaternions; explicit active.position/orientation selects changes. Use latest observation, fresh request ID, reviewed references and expected change. Inspect RGB, measured poses, references and receipts after every action. Original model_38000 UMI-4 runs50Hz, PD250Hz, fixed WristPI; geometry tools only calculate.

Live contracts override history. Single waypoint: active target within0.03m/0.10rad of measurement, duration0.5–3s; inactive components retain references. Continuous chunks:2–5 waypoints, each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m, measured-start chunk translation<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/gripper goals throughout. Start/inactive components use measured poses. Intermediate references are timed without arrival waits; future frames cross boundaries. Workspace2m from initial points.

v2.1-public-motion returns50Hz pelvis/four-point/joint traces and waypoint RGB. Inspect intermediate motion; endpoint target_reached is insufficient. Approved knots/times are public; sampled policy-input/future frames were not exposed. Foot enclosing boxes initially reach z~-0.093m with ankle z~0.035m: not exact soles/contact sensors. Negative bounds do not prove penetration.

Require pelvis translation0.20m, support-center translation0.12m; both feet unload>=0.1s, relocate>=0.06m and land. Leaning,crouching,pivots,yaw,sliding and wrist/head motion are insufficient. Require sustained clearance before horizontal foot relocation. Track floor reach separately. Respect stops below pelvis0.55m or above25-degree tilt.

MuJoCo(manifest GroundSim) episodes0001–0004 ended policy_declared_stall,native_outcome=in_progress, never success; cube remained on floor. 0001/0002: crouch,lateral shift,roll,differential wrists and25mm lift failed swing; yaw partially responded. 0003: elevated80mm endpoint and pitch±0.08rad failed; ground-return left transient ambiguity. Inactive resets confounded attribution; restoration left yaw/planar drift. Keep prior versions.

0004:3 actions/7.46s,1 timeout; motions0001–0003 have92/92/192 samples. Right then left80mm lift/0.6s plateau/return, each1.8s, had measured peak rises R0.004257/L0.002846mm. Both ground endpoints reached; neither trace verifies unloading. Pelvis shifted/lowered; both knees flexed. Different starts/inactive resets confound causality. Right-wrist50mm control rose48.705mm; return timed out with12.473mm position error. Final pelvis/support-center XY displacement23.286/0.121mm; ankle XY L3.494/R3.587mm. No manipulation.

Next: stop lift/crouch variants pending authorized public control-chain review. Seek sampled UMI-4 inputs/future frames with timestamps and link/frame semantics; compare approved knots and measured traces, accounting for inactive resets. Different wrist/ankle responses do not diagnose a defect or impossibility. Require new evidence/capability before further variants.

Wrist links are not TCPs. Derive entire-hand clearance from current finger capsule endpoints/radii. Grippers0=open,1=closed; closure proves no contact. After walking approach, clear/enclose cube, close gradually, test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop, open, withdraw both hands>=0.04m and observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Simulation pauses during reasoning; never claim realtime. Await complete replies; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions, finish_attempt may end evidenced stall; no idle budget filling.

Stop actions at rollout_finished; review public receipts and submit complete revised skill,lesson,change_summary,transfer_scope and existing evidence paths inside current rollout. Preserve versions,selections,failures,RGB,traces and receipts. No public video path for0001–0004; never invent one. Separate local revision,shared promotion,frozen evaluation. Respect returned caps and complete skill+runtime831 words/6250 characters.
