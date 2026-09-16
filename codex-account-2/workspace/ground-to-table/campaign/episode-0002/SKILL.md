---
name: loco-manip-direct
description: Learn G1 floor-cube pickup, walking and original-table placement through public physical trials.
---

# Ground cube to table

Use gpt-6-astra/xhigh through the authorized second-account launcher; no fallback. Read workspace.json, task_specification, current skill, experience_read and the required user update. Objective: walk with real alternating foot support, grasp the red floor cube, carry it airborne, release inside the original wooden tabletop, withdraw both hands and remain standing. Historical tabletop success never completes this task.

Before each physical decision record current problem, overall goal and mistakes to avoid in reason or NOTES.md. Select listed sources with experience_select before acting; reselect when failure mode changes. Reuse shared_core verification and own_tabletop_grasp_skill geometry methods, not old coordinates or outcomes. Only public listed evidence, RGB, calibration and named robot proprioception are allowed. Never inspect simulator internals, host audits, hidden object/contact/reward state, supervisor notes or other campaigns. Only registered services execute physics; no qpos writes, forces, attachment, fixed base, alternative tracker, gain/mode changes, API fallback or hardware.

Call loco_start once. Preserve and inspect initial head/right-wrist RGB; locate floor cube and original table. Ground projection z=0 applies only to visible floor points. Raised corners need depth reasoning. Derive focal length from image height/vertical FOV, reject shadows and inconsistent reprojections, and check both views when possible. Camera motion is not localization evidence for walking; named world robot poses are simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all four world metre positions and unit wxyz quaternions. Explicit active.position/orientation selects changed components; inactive components retain references. Each active target stays within 0.03m/0.10rad of current measurement; duration 0.5–3s. Workspace extends 2m from initial points. Original model_38000 UMI-4 runs50Hz, PD250Hz, fixed WristPI. Use one reviewed waypoint, latest observation and fresh request ID. State expected observable change; inspect RGB, measured poses, retained references and receipt after every action. Geometry tools only calculate targets.

Wrist links are not TCPs. Derive entire-hand clearance from current finger capsule endpoints/radii. Grippers range0 open to1 closed; closure proves no contact.

Walking requires unloading, relocation and renewed support of both feet plus sustained body translation. Track floor reach separately; leaning, crouching, ankle yaw/toe pivot, wrist/camera movement and sliding are insufficient. Prior foot-only upward/forward targets and arm-driven leaning did not establish walking. Respect controller stops below pelvis0.55m or above25-degree tilt; report, never bypass.

Episode0001 (MuJoCo; manifest GroundSim), observations0000–0007/execution0001–0007, ended policy_declared_stall after seven timeouts and23.86s physics; native outcome remained in_progress. Sources: shared_core/task_skill and own tabletop geometry methods. Wrist-left/ankle-roll preparation and differential right lift failed. Wrists down29mm plus ankles up29mm produced bilateral knee flexion about0.07/0.10→1.01/1.01rad and head descent86mm, not foot lift. Right lifts also failed from flexed posture and after opposed lateral wrist/ankle targets shifted head left121mm total. Final ankle height changes were left−0.005mm/right+0.297mm; planar shifts8.6/24.4mm with outward yaw drift. Cube remained on floor; no grasp. These observations do not prove walking impossible.

Next untested diagnostic: isolate bounded ankle attitude response with wrist/foot positions referenced, inspect named hip/knee/ankle response and restore with bounded corrections. Preserve initial yaw as a comparison; do not keep adopting yaw drift. Only if attitude control responds, test differential wrist-height/stance-roll preparation and require actual swing clearance before relocation. Do not repeat the failed coupled lifts unchanged or deepen crouch indefinitely.

After useful walking approach, clear and enclose cube, close gradually, test10–20mm lift then independent hold. Verify cube-hand co-motion and floor separation across images; relocalize after loss. Meet task height/hold/carry criteria, place well inside tabletop, open, withdraw both hands and observe at least2s.

Separate action timeout(duration+2s),180s physics budget and unlimited reasoning wait. Simulation pauses during reasoning; never claim realtime. Await complete responses; never resend uncertain actions. Two failed tests without new information require a changed hypothesis. After at least three completed actions, finish_attempt may terminate an evidenced stall; no idle budget filling.

Stop actions only at rollout_finished. Review public receipts; submit complete revised skill, lesson, change_summary, transfer_scope and existing evidence paths. Preserve versions, failures, source selection, RGB and recording/evaluation evidence; never invent a missing video. Keep local revisions separate from shared promotion and frozen evaluation. Respect returned caps and complete skill+runtime limit831 words/6250 characters.
