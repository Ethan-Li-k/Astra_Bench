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

Walking requires pelvisXY>=0.20m,support-centerXY>=0.12m,each foot airborne>=0.1s and relocating>=0.06m before landing. Measure pre-takeoff to first touchdown,excluding sliding; retain qualified low-clearance descent. Leaning/crouch/wrists alone fail. Track floor reach separately. Stop below pelvis0.55m or above25deg tilt; revise earlier on adverse trends.

MuJoCo/GroundSim failures0001–0009 remain in v8;0005 last candidate unexecuted. Reject80mm cues,long descent,loaded-foot loops,stalled rotations,forward/countervertical probes. Backoff need not raise pelvis.

0010:17actions/67.38s,stall/native in_progress,no grasp. Six steps:five.6s knots,140mm lift,180mm elevated advance,200mm landing,two progression knots,counter-swing/no wrist rise. Sixth left advance/landing140/160mm. Both feet flew; pelvis/ankle-midpointXY462/453mm. Timeouts preserve flight; midpoint is not contact.

Fixedheight paired world+Y.08 failed upright(right residual.115rad,waist unchanged). Grounded40mm descent got knees.38rad. Then five.6s ankleZ40/40/40/20/0mm,wristZ0/-20/-40/-60/-60mm got knees.92rad,pelvis.728m/tilt.818deg after removal. Posture matters.

Crouched paired+Y.08 tracked(.0045rad),flexed elbows/raised pelvis9mm; waist changed.006rad. Reverse-Y.12 residuals.092/.080rad,no extension. Local-X rolls(left+.08,right-.08) reached,tilt1.87->.125deg,shoulder-yaw changed. Following20mm descent and40mm retraction/20mm descent mostly flexed knees; finger endpoint minimum.42728m. Reject unchanged escalation.

Fixed-hand ankleZ-20mm(.5s ramp,1s plateau,.5s return) raised pelvis.723->.749m/straightened knees but flexed elbows. Recovery bilateral+120mm wristZ restored pelvis.789m/tilt1.263deg; elbows1.277/1.292->.388/.212rad while attitude residuals.180/.258rad. Untested: compare20mm descent with wrist attitudes inactive versus active from revalidated extended-arm posture. Check arm/waist,COM,tilt,clearance before lowering; no causal proof.

Wrists are not TCPs; derive whole-hand clearance from current finger capsules. Grippers0=open,1=closed; closure proves no contact. Enclose,close gradually,test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop,open,withdraw both hands>=0.04m,observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Physics pauses during reasoning; never claim realtime. Await full replies; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions finish_attempt may record stall; no idle filling.

At rollout_finished stop,review receipts; submit full skill_update:lesson,change_summary,transfer_scope,current-rollout evidence. Preserve versions,selections,failed RGB/traces/receipts. Task-local only. Obey caps and skill+runtime831 words/6250 characters.
