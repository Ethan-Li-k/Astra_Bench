---
name: loco-manip-core
description: Apply the pinned G1 UMI-4 SIMPLE task using compatible public acquisition experience and phase-specific feedback.
---

Read workspace.json, task_specification and experience_read. Use only listed public trajectories, RGB, current calibration and named robot feedback/geometry. Prefer matching task success, then compatible mechanism success, then matching counterexamples. Select few source IDs, applicability and exclusions before acting; keep 当前问题 / 总目标 / 不可重犯的错误 and the current phase/evidence in NOTES. Current task and observed interface override old recipes. Apply only the selected task delta appended below.

Call loco_start once. Use the latest observation and unique request ID. Supply all four named wrist/ankle world poses in metres and unit wxyz; declare active.position/orientation and obey measured limits. Geometry tools calculate; scalebfm_act executes. Use one waypoint unless continuous chunks are enabled. Closure0=open,1=closed is a command, not force or measured aperture; wrist origins are not calibrated grasp centres.

Observe after each action. Record phase, expected motion, measured position/attitude change and tracking residual, then the changed hypothesis. Inspect pelvis height/tilt and actual support drift when available; low tilt or ankle rise alone does not establish stable gait. Never infer object contact from robot state.

Use current render_intrinsics, pixel centres and mutually consistent views. Ray-plane projection is not depth. Check achieved wrist attitude and whole-hand sweep/closure clearance, including palm and proximal/distal fingers. Review calculation output before executing; reject predicted interference and relocalize displaced or occluded targets.

Acquire through visible opposing enclosure, gradual closure, a small observed lift and a separate hold before continuing. Check object-hand co-motion and continued visual support; closure, overlap, tipping, wrist ascent and target_reached do not prove retention. Reopen with clearance and change geometry after loss. Apply supplied human feedback only in its stated scope and preserve its tier.

Interpret timeout by phase and measured progress. Open-hand reach timeout is not a failed closed grasp; partial tracking does not establish acquisition. Unload/reconsider stance or attitude after saturation instead of repeating unchanged references. Reasoning wait, physical budget, system fault and user pause are distinct. Follow the runtime termination contract; stop at rollout_finished, preserve unverified stages and failures, and submit task-local suggestions within the combined caps. Only central publication changes loaded skills, retrieval or feedback; terminal revisions remain proposals. Do not promote empty-hand approach to loaded walking or reuse world-coordinate recipes.
