"""Add the model_38000 pelvis IMU to an in-memory SIMPLE scene only."""
import mujoco


def add_pelvis_gyro(spec):
    spec.body('pelvis').add_site(name='rsi_pelvis_imu', size=[.001]*3,
                                pos=[0, 0, 0], quat=[1, 0, 0, 0])
    spec.add_sensor(name='gyro_pelvis', type=mujoco.mjtSensor.mjSENS_GYRO,
                    objtype=mujoco.mjtObj.mjOBJ_SITE, objname='rsi_pelvis_imu')


def install_pelvis_gyro(env):
    engine = env.unwrapped.mujoco
    original = engine._build_robot
    def build_with_gyro(spec, world, actor):
        original(spec, world, actor)
        add_pelvis_gyro(spec)
    engine._build_robot = build_with_gyro
