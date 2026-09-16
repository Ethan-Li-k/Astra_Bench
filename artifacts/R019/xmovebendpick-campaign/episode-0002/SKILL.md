---
name: loco-manip-direct
description: Learn SIMPLE approach and box acquisition from public evidence.
---

## Contract

Use gpt-6-astra/xhigh. Approach the original low table, identify the rectangular cracker box among distractors, grasp with a Dex3 hand and lift at least8cm while standing. Native height and independently observed retained support are separate.

Read workspace.json, task_specification, SKILL.md and experience_read. Use workspace Python; install nothing. Inputs: listed self-experience/public trajectories, RGB, calibration, named robot state and geometry. No demonstrations, object/contact truth, evaluator/runtime inspection, other simulators or hardware. Physical actions use registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo RGB/calibration, measured/reference poses, joints, closure and geometry. Before acting, experience_select records source IDs, applicability, adaptations and exclusions; reselect when failure mechanisms change. Retrieve/adapt selected candidates; no coordinates, closure recipes or gait claims transfer.

Keep problem, goal, errors, observations and next test in notes. Use latest observation and unique request ID. State evidence, purpose and expected change in reason. Inspect fresh RGB/poses after every action; separate tracking, contact hypothesis and task progress.

Include all four absolute world poses in metres and unit wxyz: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation. Follow observed limits and inactive-component semantics. Use one waypoint unless chunks are enabled; review knots and transient clearance. Never output joints or torques. Gripper0=open,1=closed is a command, not aperture/force.

## Geometry and evidence

Use render_intrinsics, pixel centres and camera conventions. Ray-plane projection is not depth. Fit consistent visible edges in both views, inspect reprojections and retain pixel uncertainty. Transform native robot mesh vertices with current body poses; review palm, proximal and distal surfaces. Bounds are not contact or a calibrated TCP.

Endpoint clearance does not protect transient motion. Establish upward clearance before lateral withdrawal; inspect the whole sweep. Relocalize after displacement; discard stale cuboids.

Establish visible opposing enclosure before closure. Require box-hand co-motion through a small lift and separate observable hold before larger lifts. Wrist ascent, closure, target_reached and pixel overlap cannot prove grasp. After loss, reopen with clearance and change geometry; stronger closure cannot replace enclosure.

## Task-specific evidence:0001

SimpleLiveSim, not Isaac:49 actions/240s, episode_step_budget; native_outcome stayed in_progress. No grasp/lift; fingers stayed open. Box tipped during018 and remained flat. Preserve this as budget exhaustion, not native failure or early termination.

Low-arm coordination sometimes advanced support; extended arms sometimes blocked it. Withdrawal helped in some tests; no causal gait rule established. Feet advanced roughly47/37cm with outward yaw drift. Ankle rise is not sole-clearance proof.

Forward/downward reach and pitch often undertracked. Limited-active-position046 achieved23.7mm backward motion;047/048 descent still drifted forward.049 cleared without box co-motion. Active-set comparison remains unvalidated. Establish reachable stance before repeated extension.

## Continue and revise

Await complete responses; reasoning pauses physics. finish_attempt records a stall and changed hypothesis, never ends execution: test its returned next_call in the same episode. Continue useful safe tests until rollout_finished, native failure, safety/system fault or physical budget. Never substitute idle holds or model-turn completion for termination.

After termination submit complete skill_update, lesson/change_summary and existing evidence paths within all caps. Use task_specific; shared promotion requires cross-task validation and grasp regression. Preserve sources, receipts and versions; host owns recordings/outcomes.
