# UMI-4 control contract

## Signal chain

`RGB + named proprio + task + episode memory → GPT or pi0.5 → validated UMI-4
waypoints → 34-frame minimum-jerk reference → model_38000 → q29 target → 250 Hz
PD + pinned local wrist controller → MuJoCo now, SIMPLE after its backend is
connected, real runtime after separate certification`.

ScaleBFM is the tracker, not the task planner. DEX3 is controlled beside q29;
gripper closure is not packed into the ScaleBFM action.

The local wrist controller is an execution profile chosen by the host, never a
GPT action parameter. Record its name, gains, limits, code hash, tracker hash,
asset hash, and control rate in every training and evaluation manifest. Data
generated with one profile must not be silently executed with another. The
current simulation candidate is the existing deployment 6D `WristPI`, with its
original gains and limits. The harness clears integral state for inactive
position/orientation components before adding its torque to ScaleBFM PD. The
older high-stiffness Jacobian-transpose candidate is retired. WristPI has passed
the saved right-wrist position direction and world-Z rotation probes, but a
world `-Y` rotation remains outside the 0.05 rad gate; it is not certified as a
general SE(3) or hardware controller.

## Four named points

The public trajectory order is:

1. `left_wrist_yaw_link`
2. `right_wrist_yaw_link`
3. `left_ankle_roll_link`
4. `right_ankle_roll_link`

Every boundary maps by these names. In ScaleBFM's 14-body array the active
indices are `3, 6, 10, 13` in ankle, ankle, wrist, wrist order. That internal
order must never be copied positionally into the public wrist, wrist, ankle,
ankle order.

Each point contains:

- `position_world_m=[x,y,z]`: metres in one shared simulation/world frame.
- `quaternion_wxyz=[w,x,y,z]`: unit link orientation in that frame.

`rotation_vector_world_rad=[rx,ry,rz]` is an axis-angle increment: its direction
is the world-frame rotation axis and its norm is radians. A rotation about pivot
`p` changes a point to `R(point-p)+p` and changes orientation to `R*q`.

The helper `translate_target(observation, delta, names=...)` applies a world xyz
translation to selected named points. `rotate_target(observation, rotvec, pivot,
names=...)` applies the rotation above. These compile targets only; they do not
execute or prove reachability.

The dynamic equivalents are `four_point_translate` and `four_point_rotate`.
`image_pixel_to_world_plane` intersects a pixel from the latest calibrated RGB
record with an explicitly declared horizontal workspace plane; it neither
detects an object nor reads depth. `four_point_place_local_point` places an
explicit point in a wrist-link frame at a world point while preserving the
current wrist orientation. It reports the required wrist delta and whether it
fits the 3 cm single-step bound; neither geometry tool executes physics.
`loco_start` means start one locomotion-manipulation episode;
`scalebfm_act` means validate and execute a GPT-authored UMI-4 chunk;
`pi05_infer` means create one unexecuted task-policy proposal; and
`loco_execute` means execute the complete response that GPT reviewed against a
fresh proposal. `move_tcp()` is deliberately not public: TCP means tool center
point, but the DEX3 grasp TCP/closure mapping has not been calibrated. The
current controlled end-effector link is `*_wrist_yaw_link`.

Each image record binds the exposure time to its observation and includes image
size, vertical field of view, camera world pose, and the
`x_right_y_up_minus_z_forward` optical convention. A future hardware capture
provider must supply the same calibrated fields. A workspace plane may be a
task-context calibration; object pose, size, depth, simulator segmentation,
contact, and reward remain forbidden actor inputs.

Every waypoint also declares `active.position` and `active.orientation` link
names. The submitted target still contains all four poses. The host starts from
the current four-point reference and overwrites only active components; copied
inactive measured values never become hidden reference corrections. A pure
translation activates selected positions only. A rotation about a fixed pivot
normally activates both position and orientation for the selected link.
Both active lists may be empty for a pure gripper phase. In that case the
four-point reference is held, closure is linearly ramped over `duration_s`, and
the terminal status is `gripper_duration_elapsed` rather than
`target_reached`.

## Direct action

```json
{
  "request_id": "reach-0001",
  "mode": "four_point",
  "trajectory": [{
    "target": {
      "left_wrist_yaw_link": {
        "position_world_m": [0.10, 0.21, 0.73],
        "quaternion_wxyz": [1, 0, 0, 0]
      },
      "right_wrist_yaw_link": {
        "position_world_m": [0.11, -0.21, 0.73],
        "quaternion_wxyz": [1, 0, 0, 0]
      },
      "left_ankle_roll_link": {
        "position_world_m": [0, 0.12, 0.03],
        "quaternion_wxyz": [1, 0, 0, 0]
      },
      "right_ankle_roll_link": {
        "position_world_m": [0, -0.12, 0.03],
        "quaternion_wxyz": [1, 0, 0, 0]
      }
    },
    "active": {
      "position": ["right_wrist_yaw_link"],
      "orientation": []
    },
    "duration_s": 1.0,
    "grippers": {"left": 0.0, "right": 0.0}
  }],
  "reason": "small visually justified reach"
}
```

Gripper values are mechanical closure fractions: `0=open`, `1=closed`. They are
terminal commands for the waypoint's linear closure ramp, not measured gaps,
force, contact, or grasp evidence. The observation separately reports current
`gripper_commanded_closure` and `gripper_goal_closure`.

## Joint and time contracts

The tracker output q29 order is left leg 6, right leg 6, waist yaw/roll/pitch,
left arm 7, right arm 7. Transfer q29 by joint name at module boundaries.

The policy reference has 34 frames at 50 Hz. The ONNX samples offsets
`(0,1,2,3,4,25)`; its external task width is 253 and the wrapper supplies the
UMI-4 mode mask separately. PD runs at 250 Hz.

`observation_id` identifies fresh robot evidence. `request_id` identifies one
immutable semantic action, including its active masks. `status=target_reached`
requires every active position below 0.01 m and every active orientation below
0.05 rad for five consecutive 50 Hz ticks. Receipts still report position and
orientation residuals for all four links. `timed_out` is a physical tracking
failure even if the process exits normally.

A Hybrid π0.5 provider must expose an exact capability manifest before the
episode starts: `status=ready`, role `task_trained_humanoid_pi05`, actor
observation `rgb_plus_named_robot_state`, action contract
`umi4_se3_plus_bimanual_gripper`, at least `head_rgb`, a task-skill ID, and
checkpoint/normalizer SHA-256 values. A reachable WebSocket or a loaded action
head alone is insufficient. The current M3 server masks every image and is
therefore rejected for visual tasks.

`rsi/simple_bridge.py` compiles model_38000 q29 and DEX3 finger targets to
SIMPLE's `decoupled_wbc` action strictly by joint name. It does not own the
environment or advance physics. A full SIMPLE backend remains blocked until the
003 articulated asset is locally available and the reset/HOLD audit passes
offline.

The Python source of truth is `rsi/four_point.py`, `rsi/policy_harness.py`, and
`rsi/live.py`. Dynamic direct tools are `loco_start`, `four_point_translate`,
`four_point_rotate`, `image_pixel_to_world_plane`,
`four_point_place_local_point`, and `scalebfm_act`; hybrid tools are
`loco_start`, the four geometry tools, `pi05_infer`, and `loco_execute`.
`rsi/tool_host.py` dispatches and records them in one stateful episode.
`rsi/codex_app_server.py` and
`rsi/stdio_transport.py` implement the current Codex 0.154 app-server boundary.
The Direct launcher settles ScaleBFM for 5 s before exposing its first
observation. Episodes use a persistent in-memory app-server context; the host
retains audit files under its declared output root. Do not read experiment
reports or other episodes when running a zero-demonstration Direct evaluation.
