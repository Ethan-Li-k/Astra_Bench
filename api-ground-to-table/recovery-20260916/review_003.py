"""Append a source-hashed public review; never read host object/contact audit."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = Path(__file__).resolve().parent / 'episode003-review'
EP = ROOT / 'api-ground-to-table/actor-adapter/campaign/episode-0003'

def ref(p):
    return dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def save(p, v):
    with p.open('x') as f:
        f.write(json.dumps(v, ensure_ascii=False, indent=2)+'\n')

def tilt(s):
    _, x, y, _ = s['pelvis_world']['quaternion_wxyz']
    return math.degrees(math.acos(max(-1, min(1, 1-2*(x*x+y*y)))))

def main():
    observations = []
    sources = []
    for p in sorted((EP/'rollout/episode/observations').glob('*/observation.json')):
        d = json.loads(p.read_text()); sources.append(ref(p))
        observations.append(dict(id=d['observation_id'], sim_s=d['sim_s'],
            tilt_deg=tilt(d), height_m=d['pelvis_world']['position_world_m'][2],
            command_status=d['command_status'], stop_reason=d['stop_reason'], source=ref(p)))
    traces = []
    for p in sorted((EP/'rollout/episode').glob('motion_*/proprioception.json')):
        d=json.loads(p.read_text()); s=d['samples']; sources.append(ref(p))
        row=dict(motion=p.parent.name, samples=len(s), span_s=s[-1]['sim_s']-s[0]['sim_s'],
            tilt_start_deg=tilt(s[0]), tilt_max_deg=max(map(tilt,s)), tilt_end_deg=tilt(s[-1]),
            min_height_m=min(x['pelvis_world']['position_world_m'][2] for x in s),
            final_tilt_samples=[dict(sim_s=x['sim_s'],tilt_deg=tilt(x)) for x in s[-3:]], feet={})
        for link in ('left_ankle_roll_link','right_ankle_roll_link'):
            poses=[x['four_point_world'][link]['position_world_m'] for x in s]
            row['feet'][link]=dict(delta_m=[b-a for a,b in zip(poses[0],poses[-1])],
                peak_rise_m=max(x[2] for x in poses)-poses[0][2])
        traces.append(row)
    video=EP/'video/episode.mp4'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'stream=codec_name,width,height','-show_entries','format=duration,size','-of','json',str(video)]))
    assert float(probe['format']['duration']) == 18.04
    assert tilt(json.loads((EP/'rollout/episode/observations/0005/observation.json').read_text())) > 25
    frames=[]
    (OUT/'keyframes').mkdir(exist_ok=False)
    for obs in ('0002','0003','0004','0005'):
        for view in ('head_cam','right_wrist_cam'):
            p=EP/f'rollout/episode/observations/{obs}/{view}.png'
            dest=OUT/f'keyframes/{obs}-{view}.png';shutil.copy2(p,dest)
            frames.append(dict(source=ref(p),copy=ref(dest),kind='original_actor_camera'))
    review=dict(schema=1, episode='episode-0003', owner='01a0a982-cec5-71c0-b771-091c31df61f2',
        reviewed_at_unix=time.time(), backend='MuJoCo', review_complete=True,
        original_result=ref(EP/'result.json'), original_result_modified=False,
        classification='safety_stop', human_question_eligible=False,
        independent_comparable_autonomous_physical_failure_increment=0,
        observed_trigger='Pelvis tilt rose from 15.81912 to 25.00506 degrees in 0.44s; unchanged 25deg line crossed. Height 0.76562m remains above 0.55m.',
        facts=['Previous recovery ACK was target_reached but final tilt samples rose 15.65259,15.73043,15.81912 degrees.',
               'Final right foot peak rise was below 1mm. Command aborted before reference_finished.',
               'Earlier right progression started at 4.11deg yet ended at 23.82deg; low initial tilt alone is insufficient.',
               'Original head/wrist RGB show no verified enclosure/lift/carry/placement.'],
        candidate_causes=['Residual posture and rising tilt at launch left insufficient stability margin.',
                          'End-reference tracking demand and coupled wrist/support targets may contribute; arm, foot and posture variables remain confounded.'],
        rejected_inferences=['Command name does not establish root cause.','target_reached is not stable stance.',
                             'No causal controller fault or contact claim from joint commands.',
                             'One safety stop is not three independent physical failures.'],
        next_test='Fresh reset; test a less demanding landing/end-reference with measured arm placement, then inspect full tilt tail and feet before another swing. Rising tilt requires a changed support/posture probe. Falsify if comparable foot progress still produces rising terminal tilt despite reduced end-reference demand.',
        observations=observations, traces=traces, public_sources=sources, keyframes=frames,
        video=dict(source=ref(video),probe=probe,url='/videos/api-ground-episode-0003.mp4',
                   complete_continuous=True,policy_evidence=False,
                   note='Continuous physical recording includes external diagnostic view; review/policy use original actor cameras only.'))
    save(OUT/'review.json', review)
    print(json.dumps(dict(review=str(OUT/'review.json'),source_count=len(sources),video_sha256=ref(video)['sha256'])))

if __name__=='__main__': main()
