# H001 bounded reproduction decisions

## D001 — preflight
Current problem: verify original reset, runtime, controller and action history before any reproduction.
Overall goal: physically replay the original prefix through action 65, preserve all failure/mismatch evidence, no task-success credit.
Must not repeat: qpos-only teleport claimed as full state; feedback injected into baseline; inferred palm=finger pads; runtime mismatch presented as same conditions; actor/campaign creation; writes outside this directory.
Decision: inspect existing SIMPLE pipeline and snapshots; freeze thresholds before physics; use independent local script if public replay targets a different backend.

## D002 — frozen thresholds and isolated source
Current problem: original source hashes differ and no complete runtime state snapshot exists.
Overall goal: full reset + original actions 1–65, preserve dynamical history.
Must not repeat: qpos-only restoration; widening thresholds after seeing results; matching final images called same state.
Decision: archive exact-hash sources where available; otherwise copy current compatible modules to host_audit/runtime. Predeclare thresholds in thresholds.json. Material divergence stops attribution, not safe execution of the authorized prefix.

## D003 — recover audit-only export error
Current problem: attempt-001 advanced 250 settle ticks and matched the original initial named qpos exactly, then mj_saveLastXML raised No XML model loaded for SIMPLE MjSpec-compiled model. No action 1 executed. The generic host no_execution receipt does not mean no settling physics occurred.
Overall goal: complete unchanged old-action prefix with the same frozen thresholds.
Must not repeat: overwrite failed attempt; claim reset-only failure reproduces apple failure.
Decision: preserve attempt-001, skip unavailable XML export (compiled MJB already saved), add attempt name to isolated runner, start attempt-002. No controller/environment change.

## D004 — completed physical prefix; evaluate frozen criterion
Current problem: verify failed lift and all original camera files after 65 new actions.
Overall goal: freeze evidential baseline, preserve uncertainty and next single-variable specification only.
Must not repeat: exact sampled-state agreement claimed as full hidden-state identity; failed lift claimed as proof of user cause; correction actor launched.
Decision: compare all 132 RGB files, all recorded common trace fields and unchanged action payloads; evaluate the predeclared co-motion failure criterion in host_audit; derive a head-camera video clip from the new physics recording.

## D005 — freeze reproduced failure without causal overclaim
Current problem: all 10,739 recorded physics/control samples match exactly; 123/132 PNG hashes match, with tiny RGB differences in nine files; actions59–64 camera pairs all match exactly. Frozen failed-lift criterion passes for original and replay.
Overall goal: freeze baseline and hand off a single-change specification only.
Must not repeat: renderer-byte differences hidden; exact trajectory claimed full hidden-state identity; confirmation of palm-height cause without an intervention.
Decision: classify recorded physics/control as exact and RGB within the previously frozen renderer threshold; archive earliest RGB difference under host_audit. Freeze source/action/physics/video files by hashes, leave thresholds unchanged, do not execute correction actor.
