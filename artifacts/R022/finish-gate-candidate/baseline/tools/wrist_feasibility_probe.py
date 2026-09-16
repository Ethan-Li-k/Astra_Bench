"""Robot-only local IK audit of saved reference tests; no mj_step or commands.

Inspired by GPT-as-Policy's bounded DLS diagnostics. This audit does not
replace ScaleBFM or predict balance, contact, collision avoidance or success.
"""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from rsi.scalebfm import SCENE

root = Path('artifacts/R008')
output = root/'wrist_feasibility.json'
if output.exists(): raise FileExistsError(output)
model = mujoco.MjModel.from_xml_path(str(SCENE))  # Robot asset; no task cube/table.
data = mujoco.MjData(model)
root_joint = model.body_jntadr[model.body('pelvis').id]
root_q = model.jnt_qposadr[root_joint]
result = {'physical_steps':0, 'scope':'Robot-only kinematic feasibility, root and all non-right-arm joints fixed',
          'not_verified':['balance', 'collision clearance', 'dynamic tracking', 'grasp', 'hardware'],
          'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), SCENE]}, 'runs':{}}
for backend in ('onnx','continuous'):
    for axis in 'xyz':
        name = f'reference-{axis}-{backend}'
        trace = np.load(root/name/'chain.npz')
        names = trace['joint_names'].tolist(); bodies = trace['body_names'].tolist()
        qadr = np.array([model.joint(n).qposadr[0] for n in names])
        arm = [n for n in names if n.startswith('right_') and any(t in n for t in ('shoulder','elbow','wrist'))]
        aq = np.array([model.joint(n).qposadr[0] for n in arm])
        av = np.array([model.joint(n).dofadr[0] for n in arm])
        limits = np.array([model.joint(n).range for n in arm])
        wrist = bodies.index('right_wrist_yaw_link'); bid = model.body(bodies[wrist]).id
        data.qpos[:] = model.qpos0
        data.qpos[root_q:root_q+3] = trace['body_pos'][500,0]
        data.qpos[root_q+3:root_q+7] = trace['body_quat'][500,0]
        data.qpos[qadr] = trace['q_before_pd'][2500]
        mujoco.mj_forward(model,data)
        parity = float(np.linalg.norm(data.xpos[bid]-trace['body_pos'][500,wrist]))
        if parity > 1e-6: raise ValueError(f'Robot FK replay mismatch: {parity}')
        initial_q = data.qpos[aq].copy()
        goal = trace['nominal_pos'][-1,0,wrist]
        target_quat = trace['tracker_quat'][-1,0,wrist]
        target_rotation = Rotation.from_quat(target_quat[[1,2,3,0]])
        def error():
            return goal-data.xpos[bid], (target_rotation*Rotation.from_matrix(data.xmat[bid].reshape(3,3)).inv()).as_rotvec()
        before_p, before_r = error()
        for iteration in range(100):
            position, rotation = error()
            if np.linalg.norm(position)<.0005 and np.linalg.norm(rotation)<.005: break
            bounded = lambda x,cap: x*min(1.,cap/max(np.linalg.norm(x),1e-12))
            jp,jr = np.zeros((3,model.nv)),np.zeros((3,model.nv))
            mujoco.mj_jacBody(model,data,jp,jr,bid)
            jac = np.vstack([jp[:,av],jr[:,av]])
            delta = jac.T @ np.linalg.solve(jac@jac.T + .05**2*np.eye(6),np.r_[bounded(position,.02),bounded(rotation,.1)])
            data.qpos[aq] = np.clip(data.qpos[aq]+np.clip(delta,-.05,.05),limits[:,0],limits[:,1])
            mujoco.mj_forward(model,data)
        after_p,after_r = error()
        result['runs'][name] = dict(fk_replay_error_m=parity, initial_position_error_mm=float(np.linalg.norm(before_p)*1000),
            initial_rotation_error_rad=float(np.linalg.norm(before_r)), final_position_error_mm=float(np.linalg.norm(after_p)*1000),
            final_rotation_error_rad=float(np.linalg.norm(after_r)), iterations=iteration+1,
            max_total_joint_change_rad=float(abs(data.qpos[aq]-initial_q).max()),
            converged=bool(np.linalg.norm(after_p)<.0005 and np.linalg.norm(after_r)<.005))
output.write_text(json.dumps(result,indent=2))
print(json.dumps(result['runs'],indent=2))
