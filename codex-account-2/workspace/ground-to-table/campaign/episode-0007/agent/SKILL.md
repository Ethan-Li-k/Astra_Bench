---
name: loco-manip-direct
description: Learn G1 walking, floor pickup and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh through authorized second-account launcher; no fallback. Read workspace.json, task_specification, SKILL.md, experience_read and required user update through allowed sources. Goal: walk with support changes, grasp floor cube, carry airborne, release inside original wooden tabletop, withdraw hands and stand. Old tabletop success cannot count.

Record problem, goal and mistakes before decisions in reason/NOTES.md. Call experience_select before actions and on failure-mode changes: shared_core verification, own_tabletop_grasp_skill geometry, task_skill failures and listed own evidence; revalidate. Only public RGB, calibration, named robot proprioception and own command feedback are allowed. No hidden state, host audits, supervisor files or other campaigns. Registered services alone execute physics; no qpos writes, forces, attachments, fixed base, alternate tracker, gain/mode changes or hardware.

Call loco_start once; preserve initial head/wrist RGB. Locate cube/table. Project z=0 only for visible floor points, never raised corners; derive focal length from image height/vertical FOV. Reject shadows and inconsistent reprojections; check both views when visible. Robot world poses are simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all world metre positions/unit wxyz quaternions and explicit active.position/orientation. Use latest observation, fresh request ID, reviewed references and expected change. Inspect RGB, measured poses, references and receipts after every action. Original model_38000 UMI-4 runs50Hz, PD250Hz, fixed WristPI. Geometry tools only calculate.

Live contracts override history. Single waypoint: active target within0.03m/0.10rad of measurement, duration0.5–3s; inactive components retain references. Continuous:2–5 waypoints, each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m, measured-start chunk<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/gripper goals throughout; start/inactive components use measurement. Intermediate knots are timed without arrival waits; future frames cross boundaries. Workspace2m from initial points.

v2.3-atomic validates before commit. Read50Hz motion traces and waypoint RGB. Six future input frames correspond to preceding20ms interval; sample0 belongs to preceding command. Match command IDs/timestamps, approved smoothstep knots and full pelvis quaternion. Joint targets/torque are commands. Transform exact foot capsule endpoints/radii; enclosing boxes and FK are not contact sensors.

Walking requires pelvisXY>=0.20m, support-centerXY>=0.12m and both feet airborne>=0.1s, relocating>=0.06m before landing. Measure pre-takeoff to first touchdown, excluding prior sliding; retain qualified low-clearance descent. Leaning, yaw, crouch and wrist motion are insufficient. Track floor reach separately. Stop below pelvis0.55m or above25deg tilt.

MuJoCo(manifest GroundSim)0001–0004 stalled,in_progress: isolated lifts, pitch/roll and wrist/crouch variants did not verify unloading.0005 right-only coordination and extra lateral wrist preparation lacked clearance; later bilateral candidate never executed due repaired submission fault. Preserve versions; these failures prove neither impossibility nor defect.

0006:5 actions,1142 ticks/22.84s; native_failure/diagnostic_stability_stop. Action1 bilateral70mm arcs/common wrists failed clearance. Action2 counter-swing arms plus140mm arcs produced right24.29mm capsule clearance/0.26s/108.56mm airborne relocation; left diagonal swing only0.06s/46.27mm. Actions3/4 separate lift140mm, advance180mm elevated, land200mm, then two body-progression knots (five0.6s): left22.66mm/0.24s/152.77mm, right25.43mm/0.24s/157.09mm. Retrieve exact own actions, adapt measurements; arm/amplitude/start changes confound causality. After4 pelvis/supportXY279.59/251.77mm; walking evidence, not task success.

Action5 bilateral180mm descent at fixed forward reach (four45mm/0.6s knots) aborted after2.8s: tilt25.052deg,pelvisz0.7325m; tilt already18.45deg at1.8s. Lowest hand capsule remained0.460m high. Cube stayed floor; no grasp/carry/placement. Next untested: walk closer, reduce extended-arm reach, then20mm separately observed descent probes; revise at rising tilt before further descent. Never repeat the long descent unchanged.

Wrist links are not TCPs. Derive entire-hand clearance from current finger capsules. Grippers0=open,1=closed; closure proves no contact. Enclose cube, close gradually, test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop, open, withdraw both hands>=0.04m and observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Physics pauses during reasoning; never claim realtime. Await complete replies, never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions finish_attempt may document stall; no idle filling.

Stop at rollout_finished; review receipts and submit complete skill_update,lesson,change_summary,transfer_scope with existing current-rollout paths. Preserve versions,selections,failures,RGB,traces and receipts. No public0006 video path was exposed; never invent one. Task-local revision is not shared promotion or frozen evaluation. Respect returned caps and complete skill+runtime831 words/6250 characters.
