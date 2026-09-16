---
name: loco-manip-direct
description: Learn G1 walking, floor pickup and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh through authorized second-account launcher; no fallback. Read workspace.json, task_specification, SKILL.md, experience_read and required user update. Goal: walk with support changes, grasp floor cube, carry airborne, release inside original wooden tabletop, withdraw hands and stand. Old tabletop success cannot count.

Record problem, goal and mistakes before decisions in reason/NOTES.md. Before actions select shared_core, own_tabletop_grasp_skill, task_skill and listed own evidence; revalidate and reselect on failure changes. Only public RGB, calibration, named robot proprioception and own command feedback are allowed. No hidden state, host audits, supervisor files or other campaigns. Registered services alone execute physics; no qpos writes, forces, attachments, fixed base, alternate tracker, gain/mode changes or hardware.

Call loco_start once; preserve initial head/wrist RGB. Locate cube/table. Project z=0 only for visible floor points, never raised corners. Derive focal length from image height/vertical FOV; reject shadows and inconsistent reprojections; check both views when visible. Robot world poses are simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all world metre positions/unit wxyz quaternions and explicit active.position/orientation. Use latest observation, fresh request ID and reviewed references/expected change. Inspect RGB, measured poses, references and receipts after every action. Original model_38000 UMI-4 runs50Hz, PD250Hz, fixed WristPI. Geometry tools only calculate.

Live contracts override history. Single waypoint: active target within0.03m/0.10rad of measurement, duration0.5–3s; inactive components retain references. Continuous:2–5 waypoints, each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m, measured-start chunk<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/gripper goals throughout; start/inactive components use measurement. Intermediate knots timed without arrival waits; future frames cross boundaries. Workspace2m from initial points. Inactive components are not physical locks; target_reached concerns active tolerances.

v2.3-atomic validates before commit. Read50Hz traces and waypoint RGB. Six future input frames describe preceding20ms interval; sample0 belongs to preceding command. Match IDs/timestamps, approved smoothstep knots and full pelvis quaternion. Joint targets/torque are commands. Transform exact foot capsules; enclosing boxes/FK are not contact sensors.

Walking requires pelvisXY>=0.20m, support-centerXY>=0.12m and each foot airborne>=0.1s, relocating>=0.06m before landing. Measure pre-takeoff to first touchdown, excluding sliding; retain qualified low-clearance descent. Leaning/crouch/wrists alone are insufficient. Track floor reach separately. Stop below pelvis0.55m or above25deg tilt; revise earlier on adverse trends.

MuJoCo(manifest GroundSim)0001–0005 lacked verified unloading;0005 last candidate never executed(repaired submission fault).0006 stepped;180mm bilateral descent aborted at25.052deg tilt,fingers>=0.460m. Never repeat. Preserve failures; no impossibility/defect inference.

0007:24 actions/2985 ticks/59.70s; policy_declared_stall, native in_progress, no grasp. Five alternating steps adapted own0006 action4: lift140mm, advance180mm elevated, land200mm, two body-progression knots; five0.6s, counter-swing arms/no wrist rise. Retrieve exact references. Actions1/2 right/left flights0.28/0.24s, airborneXY107.13/146.22mm. After5 pelvis/supportXY406.90/373.47mm; no causal guarantee.

0007 wrists retracted80mm before20mm descent probes; unilateral descent later undertracked. Ankle40/80mm plus left-down20mm cues lowered pelvis0.787->0.745->0.666m; tilt3.82->12.65deg. Backoff40 reduced tilt but pelvis fell to0.637m. Removing elevated feet allowed further descent. Do not escalate crouch blindly.

Left attitude-only+Y0.16rad tracked but inactive wrists drifted~46mm. Active left pose then improved finger minimum to0.319m while tilt rose8.55->10.07->13.03deg; cube stayed floor. Recovery bilateral+80mm/four20mm knots ended pelvis0.688m,tilt5.19deg. No grasp/carry/place. Next untested: fixed-height fore-aft upper-body/support coordination bringing pelvis toward support center before descent. Reject further lowering without improved balance.

Wrist links are not TCPs. Derive entire-hand clearance from current finger capsules. Grippers0=open,1=closed; closure proves no contact. Enclose cube, close gradually, test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop, open, withdraw both hands>=0.04m and observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Physics pauses during reasoning; never claim realtime. Await complete replies, never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions finish_attempt may document stall; no idle filling.

Stop at rollout_finished; review receipts and submit complete skill_update,lesson,change_summary,transfer_scope with existing current-rollout paths. Preserve versions,selections,failures,RGB,traces/receipts. No public0007 video exposed; never invent one. Local revision is not shared promotion/evaluation. Respect returned caps and complete skill+runtime831 words/6250 characters.
