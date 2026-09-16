---
name: loco-manip-direct
description: Learn native SIMPLE cracker-box grasping from public visual evidence.
---

## Objective and boundaries

Use gpt-6-astra/xhigh. Identify the cracker box by visible geometry, grasp with a Dex3 hand, and lift it at least8cm while standing. Require one independently reset native success. Report native height, box-hand co-motion and visible support separately.

Read workspace.json, task_specification, SKILL.md and experience_read. Use workspace Python; install nothing. Only listed self-experience, cited public evidence, RGB, named robot state, calibration and robot geometry are allowed. No demonstrations, hidden object/contact state, evaluator/runtime inspection, other simulators or hardware. Act through registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB, calibration, measured/reference named poses, joints, closure and native geometry. Before acting, experience_select records selected sources, applicability, adaptations and rejected transfers; re-select on changed failure modes. Shared437/438 supply retrieve-test-observe-correct, gradual closure, probes and independent holds, not box coordinates or closure recipes.

Use one reviewed waypoint, latest observation path/ID and unique request ID. In reason state problem, goal, evidence, purpose, expected change and errors to avoid. After each action inspect fresh RGB and actual poses. Separate requested targets, tracking, contact hypotheses and task progress. Record uncertainty; never replay blindly.

Include all four absolute positions in metres and unit wxyz quaternions: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation; inactive components retain references. Respect0.03m translation,0.10rad rotation and0.5–3s duration limits. Keep feet supported and inspect drift. Never output q29 or torques. Closure fractions are commands, not aperture or force. Wrist frames are not calibrated TCPs. Geometry tools calculate; scalebfm_act executes.

## Geometry and control

Distinguish the white rectangular box from distractors. Ray-plane projection is not depth. Use calibrated stereo and consistent visible edges; reject shadows, occlusion and inconsistent correspondences. Head motion changes pixels. Reproject the estimated cuboid in both current views before entry; check table margin and relocalize after displacement.

Use native collision meshes, not cube capsules. Mesh vertices include geom-to-body transforms; apply current body_poses_world. Handle primitive half-sizes/transforms separately. Review palm, proximal and distal clearance through rotation, translation and closure. Bounds are conservative, not contact surfaces. Neither a low bound minimum nor a high thumb origin alone establishes useful opposition.

Robot convex surfaces versus an RGB-fitted cuboid can reject predicted interference. Sample the path and uncertainty margins, then verify physically; predictions do not prove contact. Free-space closure characterizes geometry, not a preclosure recipe.

Orientation-only actions can drift centimetres. Inspect position before reactivation. Position tracking does not imply angle tracking. Compare achieved roll/pitch/yaw with a fixed goal; bound corrections from current measurement. Flattening may disappear during descent. Change a justified variable after stalls.

## Evidence and successful candidate

0001–0005 ended via finish_attempt without native success or retention; these were policy-declared stalls, not native terminal failures. Preserve their versions: shallow/rolled entries displaced or tipped the box; stronger closure failed; descent and attitude undertracking persisted.

0006 achieved native_success at063 after63 actions/205.28s, backend SimpleLiveSim, not Isaac. A small-lift hold and endpoint support were observed, without a separate8cm endpoint dwell. One reset does not establish robustness.

Retrieve0006/042–063 as candidates after checking the new reset. Do not replay exploratory001–041. Low entry was rejected by whole-hand geometry. Stereo edge fitting estimated box x[-.375,-.312],y[-.130,.030],top.6155m (visual estimates).

It reopened/raised20mm at042, aligned forward in25mm steps043/044, then entered medially in reviewed25mm steps045–050. Attitude goal: rpy[1.30,.89,-.38], but achieved attitude differed. Mesh checks and overlays supported entry without visible displacement. Small lowering/alignment051–054 undertracked;054 measured wrist[-.3648,.0203,.7345],rpy[1.223,.925,-.524].

055–058 retained054's pose reference and closed.15,.25,.30,.35 gradually. Box stayed upright. 058 measured wrist[-.3660,.0232,.7396],rpy[1.231,.918,-.515]; thumb distal extended below the top although its origin remained above it.

059 requested15mm lift with.35 retained;060 separately held the original target2s. Wrist rose12.9mm total. Visible-edge stereo estimates supported14–16mm box rise and lateral co-motion, with pixel uncertainty.061–063 requested20/25/20mm rises. Angle error grew;063 corrected.095rad toward grasp attitude. Feet remained supported; maximum horizontal drift was about9mm. Reject the final misassociated two-edge height fit; native success supplies the threshold.

## Verification and learning

Wrist ascent, closure, target_reached and overlap do not prove grasp. Require box-hand co-motion and visible support through a10–20mm probe and separate original-target hold before larger lifts. After loss, reopen with clearance and change geometry.

Await complete responses; reasoning pauses simulation. Continue useful safe exploration, not idle holds or premature termination merely after three actions. Stop physical actions on rollout_finished. An evidenced stall may use finish_attempt with a changed hypothesis; never count it as success.

After termination submit complete skill_update, concise lesson/change_summary and existing public evidence paths within all caps. Use task_specific; shared promotion needs cross-task validation and grasp regression. Preserve prior versions/failures; host owns recording/export.
