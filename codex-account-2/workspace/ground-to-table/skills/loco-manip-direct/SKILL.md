---
name: loco-manip-direct
description: Learn G1 walking, floor pickup and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh via authorized second-account launcher; no fallback. Read workspace.json,task_specification,SKILL.md,experience_read and required user update. Goal: support-changing walking,floor grasp,airborne carry,original wooden-table release,hands withdrawn,standing. Old tabletop success cannot count.

Before decisions record problem,goal,mistakes in reason/NOTES.md. Select shared_core,own_tabletop_grasp_skill,task_skill and listed own evidence; reselect on mechanism changes. Only public RGB/calibration,named robot proprioception and own command feedback. No hidden state,host audits,supervisor files or other campaigns. Registered services alone execute physics; no qpos writes,forces,attachments,fixed base,alternate tracker,gain/mode changes or hardware.

Call loco_start once; preserve initial RGB,locate cube/table in head/wrist views. Project z=0 only for visible floor points,not raised corners. Focal length uses height/vertical FOV. Reject shadows/inconsistent reprojections; check both visible views. World poses are simulated diagnostics.

Order: left_wrist_yaw_link,right_wrist_yaw_link,left_ankle_roll_link,right_ankle_roll_link. Include all world metre positions/unit wxyz quaternions,explicit active.position/orientation. Use latest observation,fresh request ID,reviewed references/expected change. Inspect each action's RGB,poses,references,receipts. model_38000 UMI-4 50Hz/PD250Hz,fixed WristPI; geometry tools only calculate.

Live contracts override history. Single: active targets within0.03m/0.10rad of measurement,0.5–3s; inactive components retain references. Continuous:2–5 waypoints,each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m,measured-start chunk<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/grippers; start/inactive components use measurement. Timed knots,no arrival waits; future frames cross boundaries. Workspace2m from initial points. Inactive components are not locks; target_reached checks active tolerances.

v2.4 atomic validation. Read50Hz traces/waypoint RGB. Six future inputs describe preceding20ms; sample0 belongs to preceding command. Match IDs/timestamps,smoothstep knots,full pelvis quaternion. Joint targets/torques are commands. Transform exact foot capsules; FK is not contact sensing. robot_com_model uses inertias/measured FK,excludes objects/loads. Enclosing foot-box hull can overestimate support; its margin is not conservative contact evidence or dynamic stability proof. Pelvis-ankle offset is not COM.

Walking requires pelvisXY>=0.20m,support-centerXY>=0.12m,each foot airborne>=0.1s and relocating>=0.06m before landing. Measure pre-takeoff to first touchdown,excluding sliding; retain qualified low-clearance descent. Leaning/crouch/wrists alone fail. Track floor reach separately. Keep hands visibly clear of furniture when stepping. Stop below pelvis0.55m or above25deg tilt; revise earlier on adverse trends.

MuJoCo/GroundSim failures0001–0011 remain in v8–v10;0005 last candidate unexecuted. Reject80mm cues,long descent,loaded-foot loops,stalled rotations,forward/countervertical probes. Wrist active/inactive comparison belongs to isolated diagnostics.

Read own_arm_kinematic_calibration/upper-body FK. Larger elbow scalar can mean straighter arms. Use shoulder/elbow/wrist angle(0=straight),span,drop,torso/fingers;discard v10 scalar-based claims.

0012:9actions/39.52s,explicit stall/native in_progress,no grasp. Four flights;final pelvis/ankle-midpointXY317/297mm. Five.6s forward knots:140mm lift,180mm elevated advance,200mm landing,two progression knots,counter-swing,no wrist rise. Right80mm/left140mm outward additions gave width341mm. Exact deltas:0012 actions1–4;revalidate.

Backward right180/200mm,outward80mm failed flight with fixed wristXY or120/100mm wrist retraction. Millimetre foot motion;reject both.

Retraction folded arms74/67deg,spans315/327mm.40mm bilateral descent(2x.6s,fixedXY,active measured wrist attitudes) achieved40/40mm,to42/41deg. Another40mm yielded26/16mm,to15/16deg,spans384mm.20mm down/20mm retraction yielded8/8mm,to13/13deg:extension,not refolding. Pelvis783–785mm,finger endpoint minima490/522mm;no deep crouch. Reject saturated reach,not descent solely because elbow scalars rise.

Untested: brief descent during verified forward-diagonal swing's knee flexion;inspect retained torso lowering after landing. Screen hand/furniture and foot/cube clearance;no ankle-cue escalation.

Wrists are not TCPs; derive whole-hand clearance from current finger capsules. Grippers0=open,1=closed; closure proves no contact. Enclose,close gradually,test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop,open,withdraw both hands>=0.04m,observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Physics pauses during reasoning; never claim realtime. Await full replies; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions finish_attempt may record stall; no idle filling.

At rollout_finished stop,review receipts; submit full skill_update:lesson,change_summary,transfer_scope,current-rollout evidence. Preserve versions,selections,failed RGB/traces/receipts. Task-local only. Obey caps and skill+runtime831 words/6250 characters.
