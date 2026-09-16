---
name: loco-manip-direct
description: Learn SIMPLE approach and retained grasp.
---

## Contract

Approach the original low table, identify the cracker box among distractors, grasp with Dex3 and lift at least8cm while standing. Separate native height, observed retention and audit.

Read workspace.json, task_specification, SKILL.md and experience_read. Inputs: listed self-experience, RGB, calibration, named robot state/geometry; no demonstrations, object/contact truth, evaluator/runtime inspection or other simulators/hardware. 

## Retrieve, act, observe

Call loco_start once. Inspect stereo/calibration, measured/reference poses, joints, closure and geometry. experience_select records sources, adaptations and exclusions before action; reselect for changed mechanisms. Bendpick6/xmovepicksim1 inform opposition/probe/hold, not coordinates, closure or gait.

Note problem, goal, errors, observation and next test before decisions. Use latest observation/unique request ID. Inspect fresh RGB/poses after every action; distinguish tracking, contact hypothesis and progress.

Include four absolute world poses in metres/unit wxyz: left_wrist_yaw_link, right_wrist_yaw_link, left_ankle_roll_link, right_ankle_roll_link. Declare active.position/orientation. Follow current bounds/inactive semantics; multiple knots only when enabled. Review every knot and transient clearance. No joints/torques. Gripper0=open,1=closed is command, not aperture/force.

## Geometry and acquisition

Use render_intrinsics, pixel centres and camera conventions. Ray-plane projection is not depth. Fit stereo edges with reprojection/threshold uncertainty; shadowed or occluded component extrema are not box edges. Transform native meshes by body poses; inspect palm/proximal/distal surfaces. Bounds are not contact or TCP.

Review calculations before execution. Uncertain proximal intersection is not clearance; rigid plans do not protect actual tracking drift. Establish full-hand upward clearance before lateral withdrawal. Relocalize after displacement; discard stale cuboids.

Require thumb/finger opposition below the top beyond uncertainty before gradual closure. Reobserve each increment. Require box-hand co-motion through a small lift and original-target hold before larger lifts. Rotation alone, wrist rise, closure or target_reached do not prove support. After loss reopen with clearance and change geometry; stronger closure cannot replace enclosure.

## Task evidence

SimpleLiveSim, not Isaac. Episodes0001/0002 exhausted budgets without grasp/lift; preserve their histories, especially 0002 shallow closure048–049 and re-entry053 tipping the box. Ankle reference arcs are not a validated gait; establish reachable support before repeated extension.

0003:67 actions, native_success. History/observations provide a candidate, not an audited policy. 001–010 mixed advances/stalls; unloading008 preceded advance009; arcs038–039 stalled. Central/cross-body attempts lost roll/yaw; inactive wrist orientation053 worsened drift.

Candidate056–067: clear upward, return left; descent057–058 tracked39/18mm. Thumb opposed fingers~12mm below top. Closure059–061 progressed0.10/0.22/0.36. Probe062 rotated the box: hold063 alone was ambiguous. Second probe064 and independent hold065 supported co-motion/retention; vertical lifts066–067 reached native success standing. Final RGB retained the box; no post-terminal dwell was tested. Relocalize and adapt; these settings are evidence, not defaults.

## Continue and revise

Await complete inference; reasoning pauses physics. finish_attempt records a stall, not termination: test its changed next_call now. Continue useful safe tests until rollout_finished, native failure, safety/system fault or a finite evaluation budget; no idle substitutes.

After termination submit task_specific skill_update, lesson/change_summary and public evidence within caps. Preserve sources, receipts, prior versions and failures; host owns recording/export and outcome audit. Revisions are proposals; only central publication changes loaded skills.
