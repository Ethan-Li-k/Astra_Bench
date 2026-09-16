---
name: loco-manip-direct
description: Apply visual UMI-4 control with conditional chair-pushing experience.
---

## Start and select

Read workspace.json, task_specification, this skill and experience_read. Current task and observed contract govern; history supplies candidates. Use gpt-6-astra/xhigh and the exact workspace interpreter; install nothing. Use only allowed public RGB, calibration, robot state/geometry and self-experience. Never inspect hidden object/contact/evaluator state or runtime code.

Record current question, overall goal and mistakes to avoid in notes. Call loco_start once. Inspect both views, measured/reference poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptation and exclusions; reselect when failure mode changes. Grasp437/438 support retrieve-adapt-observe, not coordinate, geometry or locomotion transfer. Door16 supplies conditional unloaded approach evidence, not a loaded gait.

## Execute and verify

Use latest observation and unique request ID. State evidence, purpose and expected observable change. Include all four named wrist/ankle world positions and unit wxyz quaternions; declare active components. Follow current inactive-reference rules. Never output joints or torques. Grippers ramp 0=open,1=closed; wrists are not calibrated TCPs.

Use reported bounds. Continuous knots require explicit enablement; timed references do not guarantee steps. Review each chunk, await completion, inspect fresh RGB and measured motion including intermediate traces. Separate requested target, tracking, contact hypothesis and task progress. Tracking timeout can accompany task success; target_reached can accompany support slip.

Use render_intrinsics and pixel centers. Ray-plane projection is not depth. Reject smooth-surface, shadow, occluded or ROI-clipped stereo matches. Check full hand clearance using current mesh geometry. Hand overlap, commanded closure and wrist motion alone prove neither contact nor translation. Compare chair back, seat and caster assembly against fixed table/floor; independently withdraw to test retained displacement.

## Chair episode0001 candidate

Native SIMPLE/MuJoCo success occurred at action38,139.64 controlled seconds; independent campaign audit is separate. Retrieve public episode0001 executions/observations selectively: 7-10 coupling/withdrawal,22 stationary push,24 support-slip counterexample,35-38 changed stance and terminal push. Do not replay coordinates.

Open hands approached the broad lower back. Stationary pushes tracked better after closer stance. Growing forward error plus wrist rise signaled reach saturation: withdraw about5-6cm, restore a previously validated low height, then reassess unloaded support. Recenter hands as chair drifts. Unloading can be canceled by accumulated hand-follow motions; verify the gap again. Small differential advances may balance coverage but require visual yaw checks.

Alternating forward/apex/landing references produced useful approach but variable overshoot, stalls, increasing foot yaw and occasional4-6cm support slips. They are not a validated gait. Foot-yaw correction tracked poorly. Reject unchanged failed retries; change support sequence, timing or amplitude and inspect actual support. Action35 stalled right; alternate-left then higher-apex right moved it, but support slipped. Preserve this limitation.

## Continue and preserve

Simulation pauses during reasoning; await complete responses. A finished turn or finish_attempt stall record is not physical termination. Continue a changed safe test until rollout_finished or genuine safety/system/budget boundary. Stop physical actions immediately at termination. Submit evidence-backed task-specific skill_update; preserve failures, sources and prior versions within combined length caps. Shared promotion requires cross-task validation and grasp regression by the publisher.
