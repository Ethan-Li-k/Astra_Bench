---
name: loco-manip-direct
description: Learn G1 walking, floor pickup and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh via authorized second-account launcher; no fallback. Read workspace.json, task_specification, SKILL.md, experience_read and required user update. Goal: walk with support changes, grasp floor cube, carry airborne, release inside original wooden tabletop, withdraw hands and stand. Old tabletop success cannot count.

Record problem, goal and mistakes before decisions in reason/NOTES.md. Select shared_core, own_tabletop_grasp_skill, task_skill and listed own evidence before actions; revalidate/reselect on failure changes. Only public RGB/calibration,named robot proprioception and own command feedback. No hidden state, host audits, supervisor files or other campaigns. Registered services alone execute physics; no qpos writes, forces, attachments, fixed base, alternate tracker, gain/mode changes or hardware.

Call loco_start once; preserve initial RGB,locate cube/table in head/wrist views. Project z=0 only for visible floor points, never raised corners. Derive focal length from image height/vertical FOV; reject shadows/inconsistent reprojections; check both views when visible. World poses:simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all world metre positions/unit wxyz quaternions and explicit active.position/orientation. Use latest observation, fresh request ID and reviewed references/expected change. Inspect RGB, measured poses, references and receipts after every action. Original model_38000 UMI-4 50Hz/PD250Hz,fixed WristPI; geometry tools only calculate.

Live contracts override history. Single: active target within0.03m/0.10rad of measurement,0.5–3s; inactive components retain references. Continuous:2–5 waypoints, each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m, measured-start chunk<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/gripper goals throughout; start/inactive components use measurement. Intermediate knots timed without arrival waits; future frames cross boundaries. Workspace2m from initial points. Inactive components are not locks; target_reached concerns active tolerances.

v2.3-atomic validates before commit. Read50Hz traces/waypoint RGB. Six future input frames describe preceding20ms interval; sample0 belongs to preceding command. Match IDs/timestamps, approved smoothstep knots and full pelvis quaternion. Joint targets/torque are commands. Transform exact foot capsules; boxes/FK and pelvis-ankle offset are not contact/COM sensors.

Walking requires pelvisXY>=0.20m, support-centerXY>=0.12m and each foot airborne>=0.1s, relocating>=0.06m before landing. Measure pre-takeoff to first touchdown, excluding sliding; retain qualified low-clearance descent. Leaning/crouch/wrists alone are insufficient. Track floor reach separately. Stop below pelvis0.55m or above25deg tilt; revise earlier on adverse trends.

MuJoCo/GroundSim0001–0005:no verified unloading;0005 final candidate unexecuted(repaired fault).0006 stepped;180mm descent aborted at25.052deg.0007 fingers0.319m/tilt13.03deg, no grasp. Reject80mm ankle cue/long descent; backoff need not raise pelvis. Preserve failures; no impossibility/defect inference.

0008:stall/native in_progress,no grasp. Five steps revalidated0007; retrieve/adapt exact references. Five0.6s knots:140mm lift,180mm elevated advance,200mm landing, two body-progression knots; counter-swing arms/no wrist rise. Right/left flights0.28/0.24s,airborneXY107/146mm; pelvis/supportXY407/373mm after5. Timeouts do not erase flights; no causal guarantee.

0008 upright wrists-40mmX/ankles+20mmX worsened tilt3.27->5.50deg; reversal did not improve pelvis-support gap. Retract/+Y0.16rad:0.154rad attitude error.20mm ankleZ barely flexed knees;40mm/20mm hand descent lowered pelvis0.787->0.757m,tilt1.29deg. Retained40mm/fore-aft lowered0.713m,tilt7.26deg at fixed hand height; cue removal/wrists+20mmX reduced tilt3.40deg. 

Left20mm/+Y0.08rad first reached, then undertracked. Pure20mm descent achieved1.59mm; slower3s/-10mmX test rose0.95mm. Finger endpoint minimum0.492m, cube floor. Reject repeated rotation/descent. Bilateral+40mmZ recovery reached positions,pelvis0.787m/tilt2.28deg; inactive attitudes drifted.

Next untested: actual airborne step nearer cube, then brief crouch cue removed before reach. Revalidate clearance/posture/attitude tracking; reject loaded-foot fore-aft pulse loops. Require improved balance before lowering.

Wrists are not TCPs; derive whole-hand clearance from current finger capsules. Grippers0=open,1=closed; closure proves no contact. Enclose,close gradually,test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop, open, withdraw both hands>=0.04m and observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Physics pauses during reasoning; never claim realtime. Await full replies; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions finish_attempt may document stall; no idle filling.

At rollout_finished stop,review receipts; skill_update needs full skill,lesson,change_summary,transfer_scope,current-rollout paths. Preserve versions,selections,failures,RGB,traces/receipts. No exposed0008 video. Task-local,no shared promotion. Respect returned caps and skill+runtime831 words/6250 characters.
