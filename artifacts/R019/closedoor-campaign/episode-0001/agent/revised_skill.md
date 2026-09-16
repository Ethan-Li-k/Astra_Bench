---
name: loco-manip-direct
description: G1 UMI-4 visual control with task-local close-door evidence.
---

## Start and select

Use gpt-6-astra/xhigh. Read workspace.json, task_specification, this skill and experience_read. Use only allowed public self-experience, RGB, calibration and named robot geometry/state. No demonstrations, hidden object/contact state, evaluator inspection, other simulators or hardware. Use the exact workspace interpreter; install nothing.

Call loco_start once. Inspect stereo, calibration, measured/reference poses, joints and closure. Before acting, experience_select records source IDs, applicability, adaptations and exclusions; reselect when failure mode changes. Retrieve relevant versions and cited trajectories selectively. Record problem, goal, errors, evidence and next test in notes/reasons.

## Execute and observe

Use latest observation and unique request ID/output directory. State evidence, purpose and predicted observable change. Supply all four named wrist/ankle world poses in metres and unit wxyz; declare active position/orientation. Inactive components follow current contract. Never output joints or torques. Grippers ramp0=open,1=closed; neither closure nor wrist frames provide force, aperture or calibrated TCP.

Use reported single-waypoint limits. Continuous chunks require explicit enablement; respect segment, total duration and measured-anchor vector norms. Only scalebfm_act executes motion. Await complete responses. After every action inspect fresh RGB, actual poses and relevant intermediate traces. Separate requests, tracking, contact hypotheses and progress. Ankle rise and arrival do not establish stable support or gait. Change a justified variable after failure; avoid biased reanchoring and unchanged retries. Only explicitly unexecuted rejections may be corrected and retried.

Use render_intrinsics and pixel centers. Ray-plane projection is not depth. Reject ambiguous stereo matches, shadows and occlusion. Check whole-hand mesh clearance after posture changes. Pixel overlap, closure and wrist motion cannot prove manipulation. Test bounded interaction and independent observation/release; compare moving panel against fixed frame.

Physics pauses during reasoning. Continue until rollout_finished or actual safety/system/budget boundary. Tracking timeout is not task failure. finish_attempt records a nonterminal stall: test its changed hypothesis in this episode. Do not exhaust budget with idle holds. Stop physical actions immediately at terminal.

## Close-door candidate: episode0001

Native SIMPLE/MuJoCo success after41 actions/146.60 physical seconds; final stereo shows seated panel and standing robot. Frame-repair variant; independent audit and terminal release retention remain separate.

Initially edge-on panel projected toward robot, frame behind. Stereo supported left outer-face contact: open fingertips swept sideways, then increasingly forward as panel turned. Revalidate hinge, accessible side and direction; never replay coordinates or opening-task chunks.

Stationary sweeps5-10 closed partway. Forward undertracking with upward wrist drift signalled a reach-limit candidate. Withdraw/lower open hand, verify separation, then reposition. Unloaded arcs produced variable advances and support drift; small arcs and several later steps failed. Low-hand forward follow helped one stalled step; this is not general gait.

After approach, right hand aligned better. Raising contact improved reach; renewed saturation required unloading and stance adjustment. Near frame, reduce lateral motion and use small forward corrections away from jamb. Apparent seating and withdrawal retention were insufficient; action41's forward correction reached native completion. Do not stop merely because panel looks closed.

## Revise

After termination submit complete skill_update, lesson, change summary, scope and existing evidence. Preserve failures, selections and prior versions. Keep skill plus runtime within all reported caps. This procedure remains task_specific; shared promotion requires cross-task validation and grasp regression.
