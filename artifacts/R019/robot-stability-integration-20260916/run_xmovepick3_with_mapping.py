"""Run the existing authorized runner; inspect its actual backend without extra steps."""
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
import mujoco
import tools.learn_simple_task as runner

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'artifacts/R019/robot-stability-integration-20260916'
original = runner.create_native_task_backend

def record_mapping(*args, **kwargs):
    backend = original(*args, **kwargs)
    model, data = backend.model, backend.data
    bid = model.body('pelvis').id
    jid = int(model.body_jntadr[bid])
    address = int(model.jnt_qposadr[jid])
    tilt = float(np.rad2deg(np.arccos(np.clip(data.xmat[bid].reshape(3,3)[2,2],-1,1))))
    record = dict(actor_access=False, inspected_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        actual_formal_backend=True, extra_physics_steps=0, extra_model_or_actor_calls=0,
        env_id=args[0], seed=kwargs.get('seed'), body_name=model.body(bid).name,
        body_id=bid, safety_tilt_body_id=int(backend.adapter.body_ids[0]),
        parent_body_id=int(model.body_parentid[bid]), root_joint_name=model.joint(jid).name,
        root_joint_type=int(model.jnt_type[jid]), root_joint_qpos_address=address,
        pelvis_height_world_m=float(data.xpos[bid,2]), root_joint_height_m=float(data.qpos[address+2]),
        existing_safety_qpos2_height_m=float(data.qpos[2]), existing_safety_tilt_deg=tilt,
        public_root=backend._robot_root_observation(),
        qpos2_is_this_robot_root_height=bool(address==0 and model.jnt_type[jid]==mujoco.mjtJoint.mjJNT_FREE),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['rsi/live.py','rsi/policy_harness.py']},
        method='Read already-constructed formal backend before ordinary runner proceeds; no reset/step/observe injected. Controller and thresholds unchanged.')
    path=OUT/'actual-backend-root-mapping-xmovepick3.json'
    assert not path.exists()
    path.write_text(json.dumps(record,indent=2)+'\n')
    assert bid==backend.adapter.body_ids[0] and model.body_parentid[bid]==0
    assert record['qpos2_is_this_robot_root_height']
    assert abs(record['pelvis_height_world_m']-record['existing_safety_qpos2_height_m'])<1e-9
    return backend

runner.create_native_task_backend=record_mapping
runner.main()
