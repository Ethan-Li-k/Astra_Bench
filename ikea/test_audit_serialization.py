"""Reproduce the observed first-contact failure and verify next-version serialization."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'diagnostics/audit-serialization-fix';OUT.mkdir(parents=True,exist_ok=False)
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def backend():
    ids={'pelvis':0,'ikea_door_west':1,'left_wrist_yaw_link':2,'right_wrist_yaw_link':3}
    model=SimpleNamespace(nbody=4,body_parentid=[0,0,0,0],geom_bodyid=[1,2],
        joint=lambda name:SimpleNamespace(qposadr=[0]),body=lambda name:SimpleNamespace(id=ids[name]))
    data=SimpleNamespace(qpos=np.array([0.,0.,.755]),xmat=np.tile(np.eye(3).ravel(),(4,1)),
        ncon=1,contact=[SimpleNamespace(geom1=0,geom2=1)],time=1.)
    return SimpleNamespace(model=model,data=data,reason=None)
def force(model,data,index,out):out[0]=np.float64(1.)
old=module('old_door',ROOT/'runtime-v1/door_backend.py')
new=module('new_door',ROOT/'runtime-v2/door_backend.py')
with patch('mujoco.mj_contactForce',force):
    b=backend();audit=old.DoorEvaluator(OUT/'old');audit.reset(b)
    try:audit.update(b)
    except TypeError as e:
        (OUT/'old-failure.txt').write_text(str(e)+'\n');assert 'bool_' in str(e)
    else:raise AssertionError('Observed failure not reproduced')
    audit.stream.close()
    b=backend();audit=new.DoorEvaluator(OUT/'fixed');audit.reset(b);b.data.qpos[0]=-.6
    audit.update(b);b.data.time=2.1;audit.update(b);audit.close()
    result=json.loads((OUT/'fixed/summary.json').read_text())
    assert result['outcome']=='success' and result['hand_contact_seen'] is True
    assert len((OUT/'fixed/audit.jsonl').read_text().splitlines())==2
    (OUT/'result.json').write_text(json.dumps(dict(old_reproduced=True,new_update_and_close_pass=True,
        synthetic_only=True,no_physics_or_model_calls=True,source_result=result),indent=2)+'\n')
print('Observed bool_ fault reproduced; runtime-v2 update/close and contact-dwell outcome pass.')
