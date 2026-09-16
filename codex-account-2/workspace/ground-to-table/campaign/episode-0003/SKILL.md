---
name: loco-manip-direct
description: Learn G1 floor-cube pickup, walking and original-table placement through public physical trials.
---

# Ground cube to table

Use gpt-6-astra/xhigh through the authorized second-account launcher; no fallback. Read workspace.json, task_specification, current skill, experience_read and required user update. Goal: real alternating-foot walking, floor-cube grasp, airborne carry, release inside the original wooden tabletop, withdraw both hands and remain standing. Historical tabletop success cannot complete this task.

Before physical decisions record current problem, overall goal and mistakes to avoid in reason or NOTES.md. Call experience_select before acting and when failure mode changes. Select shared_core verification, own_tabletop_grasp_skill geometry methods and task_skill evidence; never reuse old coordinates/outcomes blindly. Only listed public evidence, RGB, calibration and named robot proprioception are allowed. No simulator internals, host audits, hidden object/contact/reward state, supervisor notes or other campaigns. Only registered services execute physics; no qpos writes, forces, attachment, fixed base, alternate tracker, gain/mode changes, API fallback or hardware.

Call loco_start once. Preserve and inspect initial head/right-wrist RGB; locate floor cube and original table. Ground projection z=0 applies only to visible floor points, never raised corners. Derive focal length from image height/vertical FOV, reject shadows and inconsistent reprojections; check both views where visible. Camera movement is not walking evidence; named world robot poses are simulated diagnostics.

Order: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Include all four world metre positions and unit wxyz quaternions. Explicit active.position/orientation selects changed components; inactive components retain references. Each active target stays within0.03m/0.10rad of current measurement; duration0.5–3s; workspace2m from initial points. Original model_38000 UMI-4 runs50Hz, PD250Hz, fixed WristPI. One reviewed waypoint, latest observation and fresh request ID. State expected observable change; inspect RGB, measured poses, retained references and receipt after each action. Geometry tools only calculate.

Wrist links are not TCPs. Derive entire-hand clearance from current finger capsule endpoints/radii. Grippers0=open,1=closed; closure proves no contact.

Require pelvis translation0.20m, support-center translation0.12m and both feet unloading>=0.1s, relocating>=0.06m and landing. Leaning, crouching, toe/heel pivot, yaw, sliding and wrist/head movement are insufficient. Track floor reach separately. Respect stops below pelvis0.55m or above25-degree tilt; never bypass.

MuJoCo (manifest GroundSim) episodes0001/0002 ended policy_declared_stall with native_outcome=in_progress, not success. Both cube-on-floor, no grasp. Episode0001: seven timeouts/23.86s; coupled wrists-down/ankles-up produced knees~1.01rad and head descent86mm, not swing. Right lifts failed near straight/flexed knees and after lateral head shift121mm. Do not repeat these preparations or deepen crouch indefinitely.

Episode0002: observations0000–0006/executions0001–0006; six actions/16.82s, four timeouts/two target_reached. Initial knees0.633/0.654rad. Right roll+0.08rad yielded measured roll−0.000038rad; yaw tests−0.08/+0.08rad yielded−0.01339/+0.03217rad yaw. Positive yaw target_reached still left0.04783rad error: partial attitude response, not walking. Differential wrists−25/+25mm with left roll−0.06rad straightened knees0.060/0.078rad. Right25mm lift then flexed both knees0.632/0.658rad; right height changed−0.000062mm. Restoration removed test demands; final planar ankle shifts3.761/4.471mm, yaw drift−0.02492/+0.04321rad. Preserve initial yaw comparison; restoration/tolerance does not erase drift.

Next untested contrast: isolate bounded sagittal ankle pitch and reversal with position references held; inspect named hip/knee/ankle response, compare roll/yaw evidence and restore initial attitude within caps. Partial yaw does not establish swing control. Require actual sustained clearance before relocation; rocking cannot count. If pitch also gives only body compensation, stop lift variations pending authorized control-chain review; public evidence does not prove impossibility or an implementation defect.

After useful walking approach, clear/enclose cube, close gradually, test10–20mm lift then independent hold. Verify cube-hand co-motion and floor separation across views; relocalize after loss. Require lift>=0.05m, hold>=0.5s and airborne horizontal carry>=0.15m. Place well inside tabletop, open, withdraw both hands>=0.04m and observe>=2s.

Separate action timeout(duration+2s),180s physics budget and unlimited reasoning wait. Simulation pauses during reasoning; never claim realtime. Await complete responses; never resend uncertain actions. Two failed tests without new information require changed hypothesis. After>=3 actions, finish_attempt may end evidenced stall; no idle budget filling.

Stop actions only at rollout_finished; then review public receipts and submit complete revised skill, lesson, change_summary, transfer_scope and existing evidence paths inside current rollout. Preserve versions, source selections, failures, RGB and recording/evaluation evidence. No video path was exposed for episodes0001/0002; never invent one. Keep local revisions separate from shared promotion/frozen evaluation. Respect returned caps and complete skill+runtime831 words/6250 characters.
