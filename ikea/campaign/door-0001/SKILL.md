---
name: loco-manip-direct
description: Open the visually identified IKEA brown bedroom door using G1 UMI-4 observations and measured action feedback.
---

Use only public RGB, calibration, named robot state/geometry and listed public experience. Read workspace.json and experience_read. Keep current problem, task goal, errors to avoid, verified progress and next test in NOTES.md. Distinguish observations from hypotheses. Hidden object poses, contacts, joint states and evaluator/runtime files are forbidden.

Applicability: model_38000 UMI-4, G1 DEX3, MuJoCo source-aligned IKEA no-latch v3. This task opens an unlatched door by contact, not handle unlocking. when_NOT_to_use: a modeled latch, different robot hand/controller, or unverified collision/layout change. No IKEA success is yet established. The host has independently reset and started this episode; use its initial observation and next_call rather than resetting.

Select public experience IDs before acting; explain interface compatibility, adaptation and exclusions. SIMPLE0012-14 used another door and hand geometry: transfer measured tracking checks, whole-hand clearance and nonterminal stall recovery; do not transplant coordinates, assumed hinge direction, reliable gait or source-scene success. Read context/simple-door-0014.md selectively, earlier versions for counterexamples. Work from this door's visible panel, frame and handle. Inspect the full hand relative to obstacles after rotations; wrist height alone is insufficient.

Actions set absolute metres and unit wxyz poses for both wrist_yaw and ankle_roll links, explicit active.position/orientation and gripper closure 0=open,1=closed. Only scalebfm_act executes. Helpers compute geometry, not contact. Use the latest observation and unique request ID; compare requested and measured motion, including public motion traces. Commands, closure and target_reached do not establish task progress.

Use the observed continuous_chunk_contract: 2-5 knots, total <=3 seconds; measured anchors, same active sets and gripper goals. Otherwise use one bounded waypoint. Inspect returned RGB and actual pose after each chunk. Physics pauses for full model reasoning; arrival timeout is tracking evidence, not an inference timeout. Replan direction, contact area, posture or approach when progress stalls; avoid blind repeats and passive idle holds.

Visually locate the brown bedroom door, establish safe hand contact, push it open, then verify sustained opening and standing. Host completion requires contact-driven opening >=30 degrees held >=1 simulated second. Continue until rollout_finished; reaching the door or low expected success does not justify stopping. finish_attempt records a changed hypothesis and continues this reset. Safety/system faults and the physical budget remain terminal. After termination, submit an evidence-backed skill_update preserving sources, failures, conditions and old versions. Shared candidates require later independent validation.
