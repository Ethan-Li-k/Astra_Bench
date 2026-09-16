---
name: loco-manip-direct
description: Learn SIMPLE approach and grasp.
---

## Contract

Use gpt-6-astra/xhigh. Approach the original low table, identify the cracker box among distractors, grasp with Dex3 and lift at least8cm while standing. Native height and observed retained support are separate.

Read workspace.json, task_specification, SKILL.md and experience_read. Use workspace Python; install nothing. Inputs: listed self-experience, RGB, calibration, named robot state/geometry. No demonstrations, object/contact truth, evaluator/runtime inspection or other simulators/hardware. Actions use registered services.

## Retrieve, act, observe

Call loco_start once. Inspect stereo/calibration, measured/reference poses, joints, closure and geometry. Before acting, experience_select records sources, applicability, adaptations and exclusions; reselect for changed mechanisms. Listed bendpick6 actions42–63 inform opposition/probe/hold, not coordinates, closure settings or gait.

Note problem, goal, errors, observation and next test before decisions. Use latest observation/unique request ID; reason states evidence and purpose. Inspect fresh RGB/poses after each action; separate tracking, contact hypothesis and progress.

Include four absolute world poses in metres/unit wxyz: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation. Follow current limits/inactive semantics; one waypoint unless chunks enabled. Review knots and transient clearance. Never output joints/torques. Gripper0=open,1=closed is command, not aperture/force.

## Geometry and acquisition

Use render_intrinsics, pixel centres and camera conventions; ray-plane projection is not depth. Fit stereo edges, check reprojections and pixel/threshold uncertainty. Transform native meshes by body poses; review palm/proximal/distal surfaces. Bounds are not contact or TCP.

Inspect calculations before action; never batch dependent review/execution. Uncertain proximal intersection is not clearance. Planned rigid-hand clearance cannot protect actual transient motion. Establish upward clearance before lateral withdrawal. Relocalize after displacement; discard stale cuboids.

Require thumb/finger opposition below the top beyond localization uncertainty before closure; marginal upper-edge overlap is insufficient. Close gradually with fresh inspection. Require box-hand co-motion through a small lift and separate hold before larger lifts. Wrist ascent, closure, target_reached and pixel overlap cannot prove grasp. After displacement/loss reopen with clearance and change geometry; stronger closure cannot replace enclosure.

## Task evidence

SimpleLiveSim, not Isaac. 0001:49 actions, budget exhausted, native in_progress, no closure/grasp/lift;018 tipped box flat. 0002:58 actions, configured240s budget exhausted, native in_progress, no grasp/lift. Feet advanced~32cm each with yaw drift. Low-hand coordination sometimes advanced support; later unloaded tests stalled. No causal gait rule; ankle rise is not sole clearance. Establish reachable stance before repeated extension.

0002 reach often coupled backward/upward drift; active-pose tests were mixed. Free-lane descent/rotation sometimes improved, but re-entry lost attitude. Shallow closure048–049 (0.10→0.20) tilted/displaced the box; open re-entry053 tipped it again. Neither proves support. Reject marginal enclosure and grasp inferred from fit. See episode0002 history/NOTES for uncertainty and review error022.

## Continue and revise

Await complete responses; reasoning pauses physics. finish_attempt records a stall, never ends execution: test its returned next_call in the same episode. Continue useful safe tests until rollout_finished, native failure, safety/system fault or physical budget; no idle substitutes or model-turn termination.

After termination submit skill_update, lesson/change_summary and evidence paths within caps. Use task_specific; shared promotion requires cross-task validation/grasp regression. Preserve sources, receipts, versions/failures; host owns recordings/outcomes.
