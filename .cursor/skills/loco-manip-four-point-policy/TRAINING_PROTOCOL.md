# Forming and extending the policy skill

## What is trained

The Codex skill supplies the harness contract, decision loop, episode memory,
and acceptance rules. It does not update GPT weights, and the upstream
GPT-as-Policy `SKILL.md` is not a learned single-task checkpoint. Task learning
comes from:

1. successful and failed closed-loop rollouts used as engineering evidence;
2. a task-trained humanoid pi0.5 checkpoint that maps RGB, task text, and robot
   state to the same four-point chunk contract;
3. selected training-split demonstrations or summaries provided as ICL when
   they improve action choice without revealing held-out state or outcomes.

The learned action is the four-point reference and gripper request. ScaleBFM,
the local wrist controller, PD gains, assets, camera calibration, and timing are
part of the pinned execution profile. Use the same profile for demonstration
collection, pi0.5 training rollouts, pi0.5-only evaluation, and hybrid
evaluation; otherwise the student learns a different reference-to-actual map.

HumanPlus-1000 or a single human video can provide motion intent and phase
boundaries. Before it becomes a target it must be retargeted by link name,
re-anchored to the robot/world frame, converted to wxyz SE(3), checked for
reachability and contacts, and executed through ScaleBFM. A raw video prompt
alone does not define metric 3D four-point targets or prove sim-to-real transfer.

Use three lifecycle states for each task adapter. `DRAFT` includes incomplete
mechanics, vision, or provider gates. `CANDIDATE` requires at least three native
training successes with fixed contract and execution-profile hashes. `FROZEN`
additionally requires at least five independent evaluation trials and at least
80% native success with no privileged actor inputs or unresolved gates. These
are current seed-task engineering thresholds, not a paper result. A frozen task
bundle contains task context, eligible demonstrations, hashes, and evaluation
receipts; trained pi0.5 weights remain a separately pinned artifact.

## Seed task

Form version 0 on `visually grasp and lift the red cube` in the current MuJoCo
scene. Use the same hidden evaluator for all methods. The actor receives only
RGB and declared robot state.

Use this curriculum:

1. HOLD all four points with both grippers open.
2. Translate each wrist on each axis, then rotate each wrist about itself.
3. Verify open/close separately for both DEX3 hands.
4. Reach above the visible red cube in short closed-loop chunks.
5. Descend, close, lift, and verify from fresh images. Do not infer grasp from
   the closure command.
6. Freeze prompt, code, thresholds, example selection, and seeds. Compare direct,
   pi0.5-only, and hybrid on the same evaluation set.

Only after the seed task passes should the same skill be extended to
pick-and-place, bimanual handling, panel pushing, and door tasks. Add a task
adapter or new training data; do not fork the low-level action contract.

## Gates

- Contract: exact four names, unit wxyz, finite values, named q29 mapping, fresh
  observations, immutable request IDs, and complete receipts.
- Tracker: HOLD and each primitive must reach the commanded reference without a
  stability stop. Report wrist and ankle errors separately.
- Vision: the task object and relevant end effector must be visible in at least
  one declared camera. A self-occluded image does not count.
- Student: pi0.5 checkpoint, normalizer, task/action schema, and hash are pinned;
  held-out chunk intent is reviewed before closed-loop use.
- Task: hidden native success, no fall, bounded commands, and reproducibility on
  frozen seeds. Keep all failures as well as successes.

## Current evidence, 2026-09-15

- The UMI-4 contract, direct/hybrid tool schemas, audited transform compilers,
  recording harness, app-server adapter/stdio transport, and three-camera
  simulation capture exist and pass the local test suite.
- Original `model_38000.onnx` HOLD reached ankle errors below 3.4 mm but timed out
  with left/right wrist errors near 2.98/2.11 cm. The seed task is not admitted.
- Head RGB shows the red cube at small scale. The current right-wrist RGB is
  heavily self-occluded and is not usable evidence.
- RGB records now carry same-observation camera calibration. The pure geometry
  chain `visible pixel → declared horizontal work plane → explicit right-palm
  local point` passed in a real settled episode without object state, depth,
  segmentation, contact, or motion. A post-hoc developer check found roughly
  2 cm planar localization error when using only the support plane; this value
  is evaluation evidence and is never fed back to the actor.
- The deployment-derived 6D WristPI now clears inactive-axis residuals and only
  integrates declared active components. In three deterministic repeats it
  reached an observation-anchored right-wrist +20 mm world-X target with 7.33 mm
  maximum active error and a +0.08 rad world-Z target with 9.50 mm position and
  0.0375 rad rotation error, without a stability stop. These prove only those
  two directions; a -0.08 rad world-Y command failed the rotation gate at
  0.0535 rad, so general orientation tracking remains unresolved. The older
  high-stiffness J-transpose controller is retired from the execution profile.
- Both DEX3 hands dynamically close and reopen in free space. A gripper-only
  waypoint now uses an empty active-point mask and linearly ramps closure over
  its duration; its terminal receipt proves elapsed command time, not contact or
  grasp success. The current grasp point/TCP and cube-width closure are not yet
  calibrated.
- A privileged developer oracle completed four small pregrasp chunks and timed
  out on the fifth before contact; cube displacement remained zero. It is not
  training, ICL, or evaluation data.
- Two vision-only reach decompositions advanced one bounded chunk and timed out
  on the second near right-wrist world-X 0.12 m. Translating all four points
  +20 mm moved both wrists within 3.7 mm but left both ankle errors near 20 mm;
  a static simultaneous foot translation is not a walking primitive. A table
  offset that made the cube visually adjacent was stable at reset but impaired
  wrist X/Z tracking; closure plus lift remained `in_progress`. That scene is
  rejected rather than tuned further.
- Hybrid startup now requires a strict π0.5 capability manifest for a visual,
  task-trained humanoid checkpoint, matching UMI-4 action schema, vision inputs,
  normalizer, and hashes. The inspected M3 server explicitly sends no image and
  is rejected for this visual task.
- A named `SimpleActionBridge` statically maps q29 and both DEX3 targets to the
  installed SIMPLE action schema without positional copying. Dynamic reset is
  blocked because articulated asset 003 is absent locally; the attempted reset
  was stopped before any automatic download. Static compatibility is not a
  connected SIMPLE backend.
- Codex app-server 0.154 passed an initialize-only handshake. No thread/turn or
  model call has run. The Direct launcher now completes and checks a 5 s
  settling phase before exposing the first observation.
- A hidden lift evaluator and stateful tool dispatcher exist. The task remains
  `DRAFT`: calibrated grasp geometry, general wrist rotation, vision-only
  closed-loop contact and lift, and dynamic SIMPLE integration remain open.

Correction (2026-09-15): these open gates do NOT prohibit the explicitly
requested zero-demonstration Direct trial. They limit interpretation and
hardware readiness. Run a bounded Direct pilot with frozen executor and RGB;
do not supply these diagnostic results or other episodes as actor examples.
Log each attempt in `ITERATIONS.md` with failure class, evidence path, retained
change, next falsifiable test, and measured model/tool accounting. A successful
demonstration is never a prerequisite for this Direct baseline.
