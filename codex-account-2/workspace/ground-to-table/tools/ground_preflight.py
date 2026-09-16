import json
import argparse
from pathlib import Path
import numpy as np
from ground_task import GroundSim,GroundEvaluator,setting_manifest,ROOT
from rsi.episode_video import EpisodeVideo

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);args=parser.parse_args()
    out=ROOT/'artifacts'/args.name;out.mkdir(parents=True,exist_ok=False)
    b=GroundSim()
    video=EpisodeVideo(b,out/'video',label='GROUND TO TABLE | setup/standing validation | no policy')
    initial={'qpos':b.data.qpos.tolist(),'qvel':b.data.qvel.tolist()}
    initial['initial_penetrating_contacts']=[{'geom1':b.model.geom(int(c.geom1)).name,'geom2':b.model.geom(int(c.geom2)).name,'distance':float(c.dist)} for c in b.data.contact[:b.data.ncon] if c.dist < -.001]
    (out/'initial_state.json').write_text(json.dumps(initial,indent=2))
    try:
        for _ in range(250):b.tick();video.record_tick('in_progress')
        e=GroundEvaluator(out/'audit');e.reset(b)
        (ROOT/'setting_manifest.json').write_text(json.dumps(setting_manifest(b),indent=2))
        for _ in range(100):b.tick();e.update(b);video.record_tick(e.outcome(b))
        images=video(out/'images') if (out/'images').mkdir(exist_ok=True) is None else None
        result={'standing_stop':b.reason,'new_task_success':False,'audit':e.audit.result(),
                'settled_pelvis':b.data.qpos[:3].tolist(),'actor_images':images}
        (out/'result.json').write_text(json.dumps(result,indent=2));e.close()
        # Independent adversarial construction: never counted as physical trial.
        guards={}
        for name in ('qpos','mass','force'):
            bad=GroundSim()
            if name=='qpos':bad.data.qpos[0]+=.1
            elif name=='mass':bad.model.body_mass[bad.model.body('diagnostic_cube').id]*=2
            else:bad.data.xfrc_applied[1,0]=1.
            bad.tick();guards[name]=bad.integrity_failure
        (out/'integrity_guards.json').write_text(json.dumps(guards,indent=2))
        assert guards=={'qpos':'external_state_write','mass':'model_or_dynamics_changed','force':'external_force'}
        # Original .755 m robot reset already has ~2 mm foot-floor penetration.
        # Reject NEW layout collisions, while recording inherited support contacts.
        from rsi.live import LiveSim
        baseline=LiveSim(wrist_pi=True)
        old={(baseline.model.geom(int(c.geom1)).name,baseline.model.geom(int(c.geom2)).name):float(c.dist)
             for c in baseline.data.contact[:baseline.data.ncon] if c.dist < -.001}
        new=[]
        for c in initial['initial_penetrating_contacts']:
            key=(c['geom1'],c['geom2'])
            if key not in old or abs(c['distance']-old[key])>.00031:new.append(c)
        (out/'layout_collision_audit.json').write_text(json.dumps({'new_layout_penetrations':new,'inherited_robot_floor_contacts':initial['initial_penetrating_contacts'],'baseline':'original LiveSim reset, same robot qpos .755 m'},indent=2))
        assert not new,new
        assert b.reason is None
        print(json.dumps({'event':'preflight_complete','result':result,'integrity_guards':guards}),flush=True)
    finally:video.close()

if __name__=='__main__':main()
