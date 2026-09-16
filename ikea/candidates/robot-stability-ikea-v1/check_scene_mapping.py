"""Static real-scene mapping check; no physics ticks, policy inference or actor."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[1]
sys.path.insert(0,str(TASK/'candidate'))
import mujoco
import numpy as np
from rsi.live import LiveSim
from rsi.scalebfm import Model38000

rows=[]
with patch.object(mujoco,'mj_step',side_effect=AssertionError('No physics steps in static mapping check')):
    for variant in ('usd-aligned-door-west-no-latch-v3','usd-aligned-fridge-hinged-no-gasket-v1'):
        scene=ROOT/'scenes'/variant/'scene.xml'
        model=mujoco.MjModel.from_xml_path(str(scene))
        data=mujoco.MjData(model);mujoco.mj_forward(model,data)
        adapter=Model38000(model,load_policy=False)
        backend=LiveSim.__new__(LiveSim);backend.model=model;backend.data=data;backend.adapter=adapter
        body=model.body('pelvis').id; joint=int(model.body_jntadr[body])
        root=backend._robot_root_observation()
        checks=dict(named_pelvis_matches_controller=int(adapter.body_ids[0])==body,
            world_parent=int(model.body_parentid[body])==0,
            freejoint=int(model.jnt_type[joint])==int(mujoco.mjtJoint.mjJNT_FREE),
            qpos_address_zero=int(model.jnt_qposadr[joint])==0,
            public_height_matches_body=root is not None and root['height_world_m']==float(data.xpos[body,2]),
            existing_height_index_equivalent=abs(float(data.qpos[2])-float(data.xpos[body,2]))<1e-12,
            exact_tilt_formula=root is not None and root['tilt_deg']==float(np.rad2deg(np.arccos(np.clip(data.xmat[int(adapter.body_ids[0])].reshape(3,3)[2,2],-1,1)))),
            sim_time_not_advanced=float(data.time)==0.)
        rows.append(dict(variant=variant,scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),
            pelvis_body_id=body,root_joint=model.joint(joint).name,root_qpos_address=int(model.jnt_qposadr[joint]),
            checks=checks,robot_root=root))
report=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=all(all(r['checks'].values()) for r in rows),
    kind='static_compiled_scene_mapping',actor_access=False,simulations_started=0,physics_ticks=0,simulated_seconds=0,
    policy_inference_calls=0,language_model_calls=0,live_actor_modified=False,scenes=rows,
    limitation='Static qpos0 mapping only; native next-episode action trace still requires validation at its authorized boundary.')
(TASK/'evidence/static-scene-mapping.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
