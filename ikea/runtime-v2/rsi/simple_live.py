"""Four-point model_38000 control attached to an already-reset SIMPLE env."""
import numpy as np

from locomanip.utils.wrist_pi import WristPI
from rsi.live import LiveSim
from rsi.simple_bridge import SimpleActionBridge


class SimpleLiveSim(LiveSim):
    def __init__(self, env, *, workspace_radius_m=2., pd_profile='native'):
        self.env = env.unwrapped
        runtime = self.env
        dt = float(runtime.mujoco.physics_dt)
        if not np.isclose(runtime.control_decimal*dt, .02):
            raise ValueError('SIMPLE must advance exactly 20 ms per tracker command')
        super().__init__(model=runtime.mjModel, data=runtime.mjData,
                         physics_dt=dt, wrist_pi=True,
                         workspace_radius_m=workspace_radius_m)
        robot = runtime.task.robot
        body_names = [self.model.joint(int(i)).name for i in robot.body_joint_index]
        hand_names = [self.model.joint(int(i)).name
                      for i in (*robot.left_hand_index, *robot.right_hand_index)]
        self.bridge = SimpleActionBridge(self.adapter.metadata['joint_names'], body_names, hand_names)
        if pd_profile == 'checkpoint':
            names = self.adapter.metadata['joint_names']
            kp = dict(zip(names, self.adapter.kp[self.adapter.policy_jnt_idx]))
            kd = dict(zip(names, self.adapter.kd[self.adapter.policy_jnt_idx]))
            for config in (runtime.sonic_config, robot.sonic_config):
                config['MOTOR_KP'] = [float(kp[n]) for n in body_names]
                config['MOTOR_KD'] = [float(kd[n]) for n in body_names]
        elif pd_profile != 'native':
            raise ValueError('pd_profile must be native or checkpoint')
        self.pd_profile = pd_profile
        policy_from_body = [body_names.index(n) for n in self.adapter.metadata['joint_names']]
        self.kp = np.asarray(runtime.sonic_config['MOTOR_KP'])[policy_from_body]
        self.kd = np.asarray(runtime.sonic_config['MOTOR_KD'])[policy_from_body]
        self.wrist_pi = WristPI(self.model, self.adapter.metadata['joint_names'],
                               self.kp, self.limits[:, 1])
        self.physics_action_calls = 0
        self._native_task_success = False
        self._native_task_reward = 0.

    def _advance_physics(self, target):
        closure = self.gripper_command_at(self.data.time)
        fingers = {name: float(closed*closure['left' if name.startswith('left_') else 'right'])
                   for name, closed in zip(self.fingers, self.closed)}
        # Native SIMPLE PD applies this extra torque as kp * delta_q. Its own
        # torque limits remain in force, and ScaleBFM action history stays raw.
        command = self.bridge.compile(target+self.wrist_pi_tau/self.kp, fingers)
        _, reward, terminated, _, _ = self.env.step(command)
        # Host-only fields: never merge native observations/info into actor packets.
        self._native_task_success = bool(terminated)
        self._native_task_reward = float(reward)
        self.physics_action_calls += 1

    def close(self):
        self.env.close()
