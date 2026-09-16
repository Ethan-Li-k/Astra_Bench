---
name: loco-manip-direct
description: Learn G1 floor-cube pickup, walking and original-table placement.
---

# Ground cube to table

Use gpt-6-astra/xhigh through the authorized second-account launcher; no fallback. Read workspace.json/task_specification, SKILL.md, experience_read and required user update. Goal: real alternating-foot walking, floor-cube grasp, airborne carry, release inside the original wooden tabletop, withdraw hands and remain standing. Old tabletop success cannot count.

Before decisions record current problem, overall goal and mistakes to avoid in reason or NOTES.md. Call experience_select before acting and when failure mode changes. Select shared_core verification, own_tabletop_grasp_skill geometry and task_skill evidence; revalidate coordinates. Only listed public evidence, RGB, calibration and named robot proprioception are allowed. No simulator internals, host audits, hidden object/contact/reward state, supervisor notes or other campaigns. Only registered services execute physics; no qpos writes, forces, attachment, fixed base, alternate tracker, gain/mode changes, API fallback or hardware.

Call loco_start once. Preserve/inspect initial head/wrist RGB; locate cube and table. Project z=0 only for visible floor points, never raised corners. Derive focal length from image height/vertical FOV; reject shadows and inconsistent reprojections. Check both views where visible. Camera motion is not walking; named world robot poses are simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all world metre positions and unit wxyz quaternions; explicit active.position/orientation selects changes. Use latest observation, fresh request ID, reviewed references and expected observable change. Inspect RGB, measured poses, retained references and receipt after every action. Original model_38000 UMI-4 runs50Hz, PD250Hz, fixed WristPI; geometry tools only calculate.

Live contracts override history. Single waypoint: active target within0.03m/0.10rad of measurement, duration0.5–3s; inactive components retain references. Newly enabled continuous chunks:2–5 waypoints, each0.5–3s,total<=3s; segment wrist/ankle translation<=0.06/0.30m, measured-start chunk translation<=0.20/0.30m; rotation<=0.10rad/segment,0.30rad/chunk. Same active links/gripper goals throughout. Start/inactive components use measured poses; intermediate references are timed without arrival waits, with future frames crossing boundaries. Workspace2m from initial points. Endpoint target_reached does not verify the intermediate trajectory.

Wrist links are not TCPs. Derive entire-hand clearance from current finger capsule endpoints/radii. Grippers0=open,1=closed; closure proves no contact.

Require pelvis translation0.20m, support-center translation0.12m; both feet unload>=0.1s, relocate>=0.06m and land. Leaning,crouching,pivots,yaw,sliding and wrist/head motion are insufficient. Require sustained clearance before horizontal relocation. Track floor reach separately. Respect stops below pelvis0.55m or above25-degree tilt.

MuJoCo(manifest GroundSim) episodes0001–0003 ended policy_declared_stall,native_outcome=in_progress, never success; cube remained on floor. Episode0001:7 timeouts/23.86s; crouching and lateral shift failed right swing. Episode0002:6 actions/16.82s; right roll+0.08 gave negligible roll; opposite yaw requests gave partial response, not swing. Differential wrist/stance-roll preparation straightened knees;25mm right lift only flexed both knees. Do not repeat.

Episode0003:obs0000–0005/executions0001–0005;5 actions/14.86s,4 timeouts. Continuous right80mm lift/0.6s plateau/return reached ground endpoint; absent intermediate measured trace leaves transient clearance unknown. Ending the next chunk80mm high timed out with80.024mm error; height rose0.00237mm while knees reached0.856/0.903rad. Positive/reversed pitch±0.08rad yielded world-Y changes−0.00001925/+0.00000657rad. Positive chunk also reset inactive references and removed lift demand; joint changes are confounded. Reversal retained references. Initial ankle attitude restoration timed out; residual yaw L−0.05350/R+0.07366rad and planar shifts4.603/6.151mm remain.

Next: stop lift/crouch variations pending authorized control-chain review. Seek public timed pelvis/ankle poses and sampled references to distinguish transient tracking, support preparation and sustained failure. Do not infer impossibility or implementation defect.

After useful walking approach, clear/enclose cube, close gradually, test10–20mm lift then independent hold. Verify cube-hand co-motion/floor separation across views; relocalize after loss. Require lift>=0.05m,hold>=0.5s,airborne horizontal carry>=0.15m. Place inside tabletop, open, withdraw both hands>=0.04m and observe>=2s.

Separate timeout(total duration+2s),180s physics budget and unlimited reasoning wait. Simulation pauses during reasoning; never claim realtime. Await complete responses; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions, finish_attempt may end evidenced stall; no idle budget filling.

Stop actions at rollout_finished; review public receipts and submit complete revised skill,lesson,change_summary,transfer_scope and existing evidence paths inside current rollout. Preserve versions,selections,failures,RGB and recording/evaluation evidence. No video path was exposed for episodes0001–0003; never invent one. Separate local revision from shared promotion/frozen evaluation. Respect returned caps and complete skill+runtime831 words/6250 characters.
