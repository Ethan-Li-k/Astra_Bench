---
name: loco-manip-direct
description: Learn the isolated G1 ground red cube to original table task through visual physical trials.
---

# Ground cube to table

Use gpt-6-astra/xhigh through the authorized second-account launcher. Read workspace.json, task_specification and experience_read. Preserve this objective: move the free-standing G1 using its legs and feet, grasp the red cube initially on the floor, carry it off the floor, release it onto the wooden table, withdraw both hands, and leave the cube stable with the robot standing. Tabletop grasp history does not complete this task.

Before every physical decision, record current problem, overall goal and mistakes not to repeat in the action reason or NOTES.md. Select relevant sources through experience_select before the first action. Only use listed public experience, current RGB, calibration and named robot proprioception. Never inspect simulator code, host audit, object/contact truth, hidden reward, supervisor notes or other campaigns. Only registered services execute physics. No qpos writes, external forces, fixed base, object attachment, alternative tracker, API fallback or hardware.

Call loco_start once. Preserve and inspect initial head/right-wrist RGB. Locate the floor cube and table visually. Ground-plane projection uses z=0 only for visible floor points; raised corners require depth reasoning. Use image height and vertical FOV for focal length, both views when possible, reject shadows and inconsistent reprojections. Named world robot poses come from simulated proprioception; this is simulation, not validated real localization.

Four-point order is left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Supply all four world metre positions and unit wxyz quaternions. Explicit active.position/orientation lists decide which components change; inactive components retain reference. Each active target is within 0.03 m / 0.10 rad of current measured pose, duration 0.5–3 s. The task workspace extends 2 m from initial points. UMI-4 original model_38000 runs at 50 Hz and original PD at 250 Hz with fixed WristPI; never change gains or mode.

Use one waypoint, the latest observation path, a fresh request ID and an evidence-based expected change. Inspect the returned images, actual positions, reference and receipt before acting again. Tools for translating, rotating or placing local points calculate targets only. Wrist links are not TCPs. Derive complete hand clearance from current finger capsule geometry. Closure fractions left/right span zero open to one closed and prove no contact.

Walking requires actual foot unloading, relocation and renewed support, with sustained body translation. Prior foot-only upward/forward target shifts and arm-driven leaning did not establish walking; avoid repeating these unchanged. Seek a distinguishable coordination hypothesis from your current observations and measured joint response. Camera/wrist motion, small ankle roll, toe pivot or sliding both feet is insufficient. Track progress toward floor reach separately from locomotion; do not replace the task with stationary reaching. The current controller stops below pelvis 0.55 m or above 25-degree tilt; report this boundary if encountered, never bypass it.

After useful approach, establish hand clearance, enclose the cube, close gradually and test a short lift followed by an independent hold. Verify cube-hand co-motion and separation from floor across images. Lost grasp requires relocalization. Transport while holding, place well inside the original tabletop, open, withdraw and observe at least 2 s. Public native outcome is only in_progress/success/failure; host phase metrics are unavailable to you.

Separate action timeout (duration plus 2 s), 180 s episode physics budget and unlimited model reasoning wait. Simulation pauses during reasoning; do not call this realtime. Await complete responses without resending uncertain actions. If a hypothesis fails twice without new information, switch diagnostic direction. After at least three completed actions, finish_attempt may end an evidenced stall with a new hypothesis; do not fill time with idle holds.

After termination, review public receipts and submit a complete revised skill, concise lesson, change_summary, transfer_scope and existing public evidence paths. Preserve failed hypotheses and sources. Skill revisions remain local; shared_candidate only proposes later review. The host enforces the complete skill plus runtime instruction cap of 831 words / 6250 characters. Learning revisions and frozen evaluation are separate.
