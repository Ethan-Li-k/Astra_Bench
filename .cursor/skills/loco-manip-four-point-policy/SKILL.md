---
name: loco-manip-four-point-policy
description: Runs and develops recorded vision-only loco-manipulation rollouts with GPT, ScaleBFM UMI-4, optional task-trained pi0.5 proposals, and MuJoCo or SIMPLE backends. Use for four-point humanoid grasping, placement, and door tasks.
---

# Loco-manip four-point policy

Use one persistent policy context for one episode. Treat the task instruction,
fresh RGB, named robot proprioception, current four-point reference, execution
receipts, and same-episode notes as the policy's evidence. Never expose object
pose, contact truth, reward, hinge state, success thresholds, or simulator state
outside the declared robot observation.

Read [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md) before producing an action. Read
[TRAINING_PROTOCOL.md](TRAINING_PROTOCOL.md) when adding a task, training pi0.5,
or deciding whether a candidate skill can be frozen.

## Tool flow

Use only a tool set actually registered by the host.

- Direct: `loco_start` → inspect all usable images and proprio → optionally
  compile a target with `four_point_translate` or `four_point_rotate`; for a
  calibrated work surface, `image_pixel_to_world_plane` may convert one visible
  pixel to a world point and `four_point_place_local_point` may convert an
  explicitly declared wrist-local point to a wrist goal → submit only bounded
  chunks to `scalebfm_act` → inspect the returned observation and receipt →
  repeat.
- Hybrid: `loco_start` → `pi05_infer` → review proposal intent and the previous
  real outcome separately → submit the reviewed final response to
  `loco_execute` → inspect the returned observation → repeat. The final
  response may copy the student proposal or replace it with a bounded
  four-point correction; the proposal file alone is never approval.
- π0.5-only evaluation executes fresh proposals through the same validator and
  backend. Do not silently add GPT corrections to this baseline.

If π0.5 or SIMPLE is marked `not_connected`, record that dependency as blocked.
Do not substitute an unrelated checkpoint or another simulator.
π0.5 is connected only after its strict capability manifest proves a
vision-enabled, task-trained humanoid checkpoint and pinned normalizer.
The launcher selects MuJoCo, SIMPLE, or a future hardware backend before the
episode. The policy never chooses or switches backend through a dynamic tool.

## Decision loop

1. State the current visible subgoal and evidence. Retract prior conclusions if
   the new image contradicts them.
2. Copy all four named poses from the latest observation and declare the active
   position/orientation links. Change only those active components. All four
   poses remain explicit; the host holds inactive components at its current
   reference instead of treating copied measured values as new targets.
3. Use 1–5 waypoints. Each waypoint is world-frame absolute SE(3), at most 3 cm
   and 0.1 rad from its observation anchor, with 0.5–3.0 s duration.
   A pure gripper phase may leave both active lists empty; its closure ramps
   over the waypoint duration and proves only that the command interval ended.
   A local-point compiler may return a farther geometric goal; when
   `within_single_step_limit=false`, approach it through fresh, bounded chunks.
4. Execute once with a unique `request_id`. Never retry an uncertain transport
   result and never reuse an ID for different content.
5. Treat `accepted`, `executing`, a gripper command, and an IK/FK target as
   requests. Only fresh RGB, measured poses, tracking error, and native outcome
   are execution evidence.
6. Stop the capability trial on nonfinite state, stability stop, stale plan,
   repeated tracker timeout, or unusable vision. Log the failure class and move
   to the next unresolved dependency.

Do deterministic interface and tracker checks before spending a model call.
The policy must not output q29, action29, torque, privileged waypoints, or a
whole open-loop task script.

## Episode memory

Keep same-episode notes concise: verified completed subgoals, current attempt,
remaining work, failed approach, and the visual or receipt evidence. Do not load
evaluation outcomes from other seeds into a frozen test episode.

Across tasks, preserve the tool contract, task-agnostic corrections, calibrated
camera facts, and failure taxonomy. Task-specific demonstrations belong to the
training split for the task-trained policy; they are not hidden ICL answers for
held-out episodes.
