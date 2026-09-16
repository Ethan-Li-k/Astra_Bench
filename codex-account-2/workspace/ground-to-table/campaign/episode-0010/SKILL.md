---
name: loco-manip-direct
description: Learn G1 walking, floor pickup and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh via authorized second-account launcher; no fallback. Read workspace.json,task_specification,SKILL.md,experience_read and required user update. Goal: support-changing walking,floor grasp,airborne carry,original wooden-table release,hands withdrawn,standing. Old tabletop success cannot count.

Record problem,goal,mistakes before decisions in reason/NOTES.md. Select shared_core,own_tabletop_grasp_skill,task_skill and listed own evidence before actions; reselect on failure changes. Only public RGB/calibration,named robot proprioception and own command feedback. No hidden state,host audits,supervisor files or other campaigns. Registered services alone execute physics; no qpos writes,forces,attachments,fixed base,alternate tracker,gain/mode changes or hardware.

Call loco_start once; preserve initial RGB,locate cube/table in head/wrist views. Project z=0 only for visible floor points,never raised corners. Focal length uses height/vertical FOV. Reject shadows/inconsistent reprojections; check both views when visible. World poses are simulated diagnostics.

Order: left_wrist_yaw_link,right_wrist_yaw_link,left_ankle_roll_link,right_ankle_roll_link. Include all world metre positions/unit wxyz quaternions,explicit active.position/orientation. Use latest observation,fresh request ID,reviewed references/expected change. Inspect RGB,poses,references,receipts after every action. model_38000 UMI-4 50Hz/PD250Hz,fixed WristPI; geometry tools only calculate.

Live contracts override history. Single: active targets within0.03m/0.10rad of measurement,0.5–3s; inactive components retain references. Continuous:2–5 waypoints,each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m,measured-start chunk<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/gripper goals throughout; start/inactive components use measurement. Knots are timed,no arrival waits; future frames cross boundaries. Workspace2m from initial points. Inactive components are not locks; target_reached checks active tolerances.

v2.4 retains atomic validation. Read50Hz traces/waypoint RGB. Six future inputs describe preceding20ms; sample0 belongs to preceding command. Match IDs/timestamps,approved smoothstep knots and full pelvis quaternion. Joint targets/torques are commands. Transform exact foot capsules; boxes/FK are not contact sensors. robot_com_model uses known inertias/measured FK,excludes objects/loads; use with geometry/motion trends. Pelvis-ankle offset is not COM. Foot-hull COM projection is not dynamic stability proof.

Walking requires pelvisXY>=0.20m,support-centerXY>=0.12m,each foot airborne>=0.1s and relocating>=0.06m before landing. Measure pre-takeoff to first touchdown,excluding sliding; retain qualified low-clearance descent. Leaning/crouch/wrists alone fail. Track floor reach separately. Stop below pelvis0.55m or above25deg tilt; revise earlier on adverse trends.

Prior MuJoCo/GroundSim failures:0001–0005 unloading unverified;0005 last candidate unexecuted;0006 tilt stop;0007/0008 reach stalls. Reject80mm cues,long descent,loaded-foot loops,stalled rotations. Backoff need not raise pelvis.

0009:23actions/73.70s,stall/native in_progress,no grasp. Five0.6s walking knots:140mm lift,180mm elevated advance,200mm landing,two progression knots,counter-swing arms/no wrist rise. Sixth left140/160mm advance/landing flew0.22s/145mm; pelvis/ankle-midpointXY462/453mm. Timeout does not erase flight; no gait guarantee.

Brief40mm cue/retraction did not recruit knees. Fixedhand40mm cue,0.5s ramp/2s plateau/0.5s return transiently flexed knees~0.56rad then rebounded. Action11 five0.6s knots,ankleZ40/40/40/20/0mm,both wristZ0/-20/-40/-60/-60mm lowered hands~55mm,pelvis0.736m/tilt1.02deg after removal. Grounded20mm descents progressed; inspect settling.

Left fixedheight+Y0.08rad tracked within0.012rad in crouch. Retraction40mm improved tilt; descent worsened it. Bilateral+40mmX reached but waist pitch stayed nearzero,tilt7.71deg. After withdrawal/right rise,left-20/right+20mm raised tilt10.42deg with little waist-roll change. Finger endpoint minimum0.33498m,cube floor. COM stayed inside conservative foot hull(min71mm during reach),despite adverse posture trends. Not solved reach primitives.

Recovery left+80/right+40mmZ twice restored pelvis0.779m/tilt1.59deg. Untested: paired wrist attitudes at fixed heights; require waist/arm redistribution and favorable pelvis/COM trends before descent.

Wrists are not TCPs; derive whole-hand clearance from current finger capsules. Grippers0=open,1=closed; closure proves no contact. Enclose,close gradually,test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop,open,withdraw both hands>=0.04m,observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Physics pauses during reasoning; never claim realtime. Await full replies; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions finish_attempt may document stall; no idle filling.

At rollout_finished stop,review receipts; submit full skill,lesson,change_summary,transfer_scope,current-rollout evidence. Preserve versions,selections,failures,RGB,traces/receipts. Task-local,no shared promotion. Respect returned caps and skill+runtime831 words/6250 characters.
