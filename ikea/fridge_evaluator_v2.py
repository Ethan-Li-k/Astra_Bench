"""Host-only next-task criterion. Never import this into the policy tool context."""
import json
from pathlib import Path
import mujoco
import numpy as np


class FridgeEvaluator:
    contract='ikea-fridge-upper-hand-drive2deg-open45-hold1-stable-v2'

    def __init__(self,output):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.stream=(self.output/'audit.jsonl').open('x',buffering=1)

    def reset(self,b):
        m,d=b.model,b.data
        self.addresses={s:int(m.joint(f'ikea_fridge_{s}_hinge').qposadr[0]) for s in ('left','right')}
        self.initial={s:float(d.qpos[q]) for s,q in self.addresses.items()}
        self.leaves={m.body(f'ikea_fridge_{s}').id:s for s in self.addresses}
        self.hands={m.body(f'{s}_wrist_yaw_link').id for s in ('left','right')}
        # Parents precede children in the compiled model.
        for i in range(m.nbody):
            if int(m.body_parentid[i]) in self.hands:self.hands.add(i)
        self.since={s:None for s in self.addresses}
        self.drive={s:0. for s in self.addresses}
        self.previous={s:0. for s in self.addresses}
        self.max_open={s:0. for s in self.addresses}
        self.max_hold={s:0. for s in self.addresses}
        self._outcome='in_progress';self.last=None

    def update(self,b):
        m,d=b.model,b.data;contacts=[];t=float(d.time)
        for i in range(d.ncon):
            c=d.contact[i];a,z=[int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
            if a in self.leaves and z in self.hands:leaf,hand=a,z
            elif z in self.leaves and a in self.hands:leaf,hand=z,a
            else:continue
            force=np.zeros(6);mujoco.mj_contactForce(m,d,i,force)
            if force[0]>.01:
                contacts.append(dict(door=self.leaves[leaf],robot_body=m.body(hand).name,normal_force_n=float(force[0])))
        rot=d.xmat[m.body('pelvis').id].reshape(3,3)
        tilt=float(np.arccos(np.clip(rot[2,2],-1,1)));base=float(d.qpos[2])
        stable=bool(base>.55 and tilt<np.deg2rad(35) and b.reason is None)
        leaf_rows={}
        for side,q in self.addresses.items():
            angle=(float(d.qpos[q])-self.initial[side])*(-1 if side=='left' else 1)
            contact=any(c['door']==side for c in contacts)
            if contact:self.drive[side]+=max(0.,angle-self.previous[side])
            qualified=bool(angle>=np.pi/4 and self.drive[side]>=np.deg2rad(2.) and stable)
            if qualified:
                if self.since[side] is None:self.since[side]=t
                dwell=t-self.since[side]
            else:self.since[side]=None;dwell=0.
            self.previous[side]=angle
            self.max_open[side]=max(self.max_open[side],angle)
            self.max_hold[side]=max(self.max_hold[side],dwell)
            leaf_rows[side]=dict(open_rad=angle,hand_contact=contact,contact_positive_motion_rad=self.drive[side],
                qualified=qualified,qualified_dwell_s=dwell)
        success=any(row['qualified'] and row['qualified_dwell_s']>=1. for row in leaf_rows.values())
        self._outcome='failure' if b.reason else 'success' if success else 'in_progress'
        self.last=dict(sim_s=t,doors=leaf_rows,contacts=contacts,base_z=base,tilt_rad=tilt,
            stable=stable,safety_reason=b.reason,outcome=self._outcome)
        self.stream.write(json.dumps(self.last)+'\n')

    def outcome(self,b):return self._outcome

    def close(self):
        if self.stream.closed:return
        self.stream.close()
        (self.output/'summary.json').write_text(json.dumps(dict(contract=self.contract,actor_access=False,
            minimum_hand_driven_open_deg=2.,initial_angles_rad=self.initial,max_open_rad=self.max_open,max_hold_s=self.max_hold,
            native_outcome=self._outcome,last=self.last),indent=2)+'\n')
