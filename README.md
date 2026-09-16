# Astra Bench — RSI source snapshot

This source tree is captured at the fixed timestamp in [SOURCE_PROVENANCE.json](SOURCE_PROVENANCE.json). That record distinguishes the original source snapshot, this bounded core/UI increment and historical evidence. Per-file SHA256 values and executable modes are in the companion manifest. GitHub commit and upload status are supplied by the root publisher's external receipt; they are not inferred from local files.

RSI studies visual humanoid manipulation with named wrist/ankle four-point control, G1/DEX3 and the model_38000 controller family. Reported physical runs use **MuJoCo**. Simulation pauses during model planning: these are not real-time closed-loop or real-robot results. The policy remains gpt-6-astra/xhigh, using the authorized auxiliary account or explicitly authorized direct API transport.

## Six exact tasks

The current [six-task rules](ref/USER_UPDATE_20260916_SIX_TASK_FOCUS.md) take precedence over historical instructions. Ground-cube transport and IKEA exploration remain paused. The original SIMPLE README mapping is:

- XMovePick: `simple/G1WholebodyXMovePickTeleop-v0`
- BendPick: `simple/G1WholebodyBendPickMP-v0`
- Handover: `simple/G1WholebodyHandoverTeleop-v0`
- Mobile P&P: `simple/G1WholebodyLocomotionPickBetweenTablesTeleop-v0`
- Grasp: `simple/G1WholebodyTabletopGraspMP-v0`
- XMoveBendPick: `simple/G1WholebodyXMoveBendPickTeleop-v0`

MP asset/control adaptation is tracked separately. The MP name does not authorize a privileged planner, a robot change, or a near-match task substitution. BendPickTeleop, BendPickSimToReal, MobilePickAndPlaceCheezit and earlier tabletop block results cannot substitute for the exact MP/BetweenTables entries. The previous 91-entry inventory remains historical.

Each exact task follows adaptation, learning, **five consecutive independently audited successes under one fixed complete candidate**, then a separately preregistered **ten-episode frozen evaluation**. Changes to skill, allowed experience/retrieval, feedback, control or assets create a new candidate and restart its streak. Historical and already in-flight trials are not retroactively registered. The candidate freezes the whole policy input/configuration, not only SKILL.md. Evaluation suggestions stay outside subsequent frozen policy loads. Passing 5/5 is an admission gate, not proof of broad reliability.

The latest learning-horizon instruction makes self-imposed cumulative time/action/model-turn limits nonterminal progress checkpoints before the stability gate. Real safety, user pause, irrecoverable system errors, native noncontinuable termination and authorized global budget constraints still apply; unknown requests/actions are not repeated. Extended learning horizons are labeled separately from the original timed benchmark. Frozen trials retain their preregistered finite budget. This new instruction does not rewrite the real endings or denominator treatment of older episodes.

## Historical evidence and current scores

[docs/public-results-index.json](docs/public-results-index.json) is a fixed, public-field projection of local audit records with source hashes and audit times. It separates exact task, initialization/control variant, historical/current cohort, native versus complete semantic audit, human assistance and frozen evaluation. No eligible samples means **not evaluated**, not 0%. Properly sealed and audited physical-budget exhaustion and safety stops count as unsuccessful valid attempts under the applicable recorded protocol; infrastructure/unknown outcomes remain separately visible.

- R018 records 10 audited native block-grasp successes in 15 physical attempts; its stricter `terminal_successes` count is 5. The 423 infrastructure-only records are not physical attempts. This is fixed-scene adaptive learning, not held-out generalization or the current TabletopGraspMP score.
- R019 records 10 audited successes for the **SIMPLE asset003 push-open variant**. Geometry/collision revisions and completion contracts define that result; it does not prove performance in an unmodified original scene or IKEA.
- Related box/apple and locomotion experience retains its task, grasp, feedback and control conditions. Empty-hand motion, load transport, retention, handover, placement/release and final hold are separate capabilities. A command or target-arrival ACK does not establish task success.

Original videos, raw trajectories, private model logs and detailed host-state dumps remain local. The old R017 README is retained as [historical documentation](docs/HISTORICAL_ROOT_README_R017.md).

## Skills and source organization

The snapshot contains a complete captured group of `rsi/`, `tools/`, `tests/`, `skills/`, `.cursor/skills/` and `actor_context/`, plus the verified UI source, branch engineering source, necessary configurations and reference documentation. Both `rsi/frozen_skill.py` and `tests/test_frozen_skill.py` are included together. Each changed group passed two consecutive content-hash reads before copying; later live changes are outside this fixed capture.

GPT-as-Policy is the primary reference for short task/context/control contracts, persistent episode context and replanning from actual ACKs; RoboRSI is secondary for atomic stages, prerequisites and verification. Entry plus runtime budgets remain 831 words / 6250 characters / 5357 non-whitespace characters.

The [central skill ownership rule](ref/USER_UPDATE_20260916_CENTRAL_SKILL_OWNER.md) assigns shared/atomic skill semantics and publication to the framework owner; SIMPLE retains physical scheduling and independent task audit. Actor skill edits are proposals, not automatically published next-episode policy. Success-conditioned atomic experience is retrieved before compatible counterexamples; source coordinates are not copied into a different task. Frozen batches do not absorb concurrent new experience.

Central publication and learning-horizon integration are engineering work in progress at capture. [docs/CENTRAL_SKILL_CAPTURE.md](docs/CENTRAL_SKILL_CAPTURE.md) records the captured receipts and development classification; no deployment or physical benefit is inferred from code presence. The mapping-correction directory contains seven actor text candidates and separate **host-only** contracts/reviews. Its static root acceptance does not authorize mounting the entire review directory into an actor. Historical publisher names in older handoffs are superseded by the current central-owner instruction.

## Local web reports

The existing full-project report remains at `http://127.0.0.1:8765/`, including its original hash routes. The separate verified six-task page is `http://127.0.0.1:8765/simple-six`; both use the same server. The UI owner's completed result and root browser resolution are copied with matching source hashes. A later `benchmark-alignment` owner changed live files during preparation; this snapshot pins the completed six-task-page version using that owner's retained pre-edit backup. Its later development changes are outside this fixed UI version. Every relocated source path is recorded in SOURCE_PROVENANCE.

The new page displays actual numerators/denominators, native and semantic audit rates, assistance strata, unknown/no-sample states, candidate/frozen stages, evidence-bound required questions and an active suggestion entry. Historical success cannot label a newer unfinished episode as completed. Recorded owner tests cover both routes, budget/safety denominator handling, real video Range playback/seeking, refresh preservation and feedback context; this source capture does not rerun the browser or server.

See [LOCAL_WEB_REPORTS.md](docs/LOCAL_WEB_REPORTS.md) for the common local startup method. The full service needs locally retained, hash-verified evidence/media omitted from this source tree. A clone alone cannot reproduce the complete live feedback service. A localhost URL is not a GitHub-hosted public deployment, and no public feedback API or account queue is exposed by publishing source.

## Dependencies, exclusions and provenance

[DEPENDENCIES.md](docs/DEPENDENCIES.md) describes external locomanip/SIMPLE/assets and existing environment assumptions. Model weights, installed environments, binary assets, recordings and frames are not bundled. Snapshot checks validate source/structure, not a newly installed simulator or a new robot attempt.

Credentials, account/session directories, raw model JSONL/logs, databases, nested Git metadata and symlinks are excluded before copying. Secret scans report only paths/categories and explanations. Protected account directories are not enumerated; their recursive size/count is explicitly unknown. Eight previously withheld helper/test sources remain excluded, along with the damaged historical status file; primary source coverage is recorded independently.

Existing third-party licenses and notices are retained; [THIRD_PARTY_AND_ASSETS.md](docs/THIRD_PARTY_AND_ASSETS.md) describes their scope. No new first-party license grant is added. Source hashes, the previous snapshot and the final increment make the exact tree independently reviewable.
