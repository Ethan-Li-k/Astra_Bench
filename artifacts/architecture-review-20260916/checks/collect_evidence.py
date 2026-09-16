"""Read existing receipts only; no simulator/model imports and no upstream writes."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import subprocess

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
sources={}

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def register(p):
    p=Path(p); sources[str(p)]={'sha256':digest(p),'bytes':p.stat().st_size}

def read(p):
    p=Path(p); register(p); return json.loads(p.read_text())

def video(p):
    register(p)
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream=duration,nb_frames,r_frame_rate','-of','json',str(p)],capture_output=True,text=True,check=True)
    return {'path':str(p),'sha256':sources[str(p)]['sha256'],**json.loads(r.stdout)['streams'][0]}

def brief_result(p):
    d=read(p)
    keys=('episode_id','success','overall_success','native_outcome','stop_reason','backend_stop_reason',
          'actions','sim_s','wall_s','error','skill_updated','starting_skill_sha256','model','effort',
          'human_feedback_used','human_demonstration_used','terminal_kind','physical_failure','api_calls')
    return {k:d[k] for k in keys if k in d}

def termination(r):
    if r.get('error'):return 'infrastructure_interruption'
    if r.get('success'):return 'native_success_pending_task_audit'
    if r.get('backend_stop_reason'):return 'safety_stop'
    return {'policy_declared_stall':'policy_early_stop','episode_step_budget':'physical_budget_truncation',
            'api_batch_call_limit':'batch_budget_truncation'}.get(r.get('stop_reason'),r.get('stop_reason') or 'unfinished')

report={'snapshot_started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'actor_access':False,'source_thread_access':'Supplied public user/assistant excerpts; no desktop wake/resume',
        'scope':'learning successes, not frozen evaluation/generalization; paused inference, not realtime',
        'tasks':{},'representative_public_decisions':[]}
audit=read(ROOT/'artifacts/R018/audit_summary.json')
counted=[]
for row in audit['episodes']:
    if not row.get('audited_native_success'):continue
    ep=ROOT/'artifacts/R018/campaign'/row['episode_id']
    raw=brief_result(ep/'result.json'); ev=read(ep/'evaluation.json'); turn=read(ep/'turn_001.json')
    raw.update(audited_native_success=True,endpoint_retained=row['terminal_success'],
               complete_turn=turn.get('status')=='completed',
               native_hold_s=row['audit']['longest_qualifying_hold_s'],
               endpoint_hold_s=row['audit']['terminal_qualifying_hold_s'],video=video(ep/'video/episode.mp4'))
    counted.append(raw)
report['tasks']['table_cube']={'claimed':10,'verified':len(counted),'physical_attempts':audit['physical_attempts'],
    'completed_records':audit['completed_records'],'infrastructure_only_records':audit['infrastructure_only_records'],
    'endpoint_retained':audit['terminal_successes'],'episodes':counted,'backend':'MuJoCo LiveSim / G1 DEX3 / ScaleBFM UMI-4',
    'human_feedback_tier':'autonomous self-experience/no demonstrations; old receipt lacks explicit human_feedback_used field',
    'reset_qualification':'Existing audit counts distinct fresh-backend episodes in a fixed scene. Legacy receipts predate SIMPLE reset UUID schema; no UUID retrofilled. Raw results, original videos and saved-state audits inspected.',
    'setting':'red tabletop cube; >=0.05m rise and >=0.5s hold standing; identical reset scene, not randomized held-out trials'}
for task in ['door','bendpick','apple','faucet','boxplace']:
    base=ROOT/f'artifacts/R019/{task}-campaign'; rows=[]
    for ep in sorted(base.glob('episode-*')):
        if not (ep/'result.json').exists():
            rows.append({'episode_id':ep.name,'state':'incomplete_at_snapshot','counted':False});continue
        r=brief_result(ep/'result.json'); scene=read(ep/'video/scene_setup.json') if (ep/'video/scene_setup.json').exists() else {}
        review=read(ep/'success_review.json') if (ep/'success_review.json').exists() else {}
        feedback=read(ep/'human_feedback_review.json') if (ep/'human_feedback_review.json').exists() else {}
        r.update(state='completed',termination_class=termination(r),counted=review.get('audited_task_success') is True,
                 reset=scene.get('reset_provenance'),frame_revision=scene.get('frame_collision_override',{}).get('id','original'),
                 human_feedback_used=r.get('human_feedback_used',False) or feedback.get('human_feedback_used',False),
                 human_feedback_basis='result plus separate exposure review; absent old flags are not fabricated',
                 controller=scene.get('pd_profile','not_recorded_here'))
        if r['counted']:
            r['termination_class']='audited_task_success'
            r.update(video=video(ep/'video/episode.mp4'),review_path=str(ep/'success_review.json'),
                     skill_after=review.get('skill_sha256'),skill_version_after=review.get('skill_version'),
                     independent_reset_verified=review.get('independent_reset_verified'),
                     dwell_s=review.get('longest_qualified_dwell_s'),final_opening_deg=review.get('final_opening_deg'),
                     host_grasp_audit=review.get('host_audit'),reviewed_hashes={})
            for rel,expected in review.get('evidence_sha256',{}).items():
                p=ep/rel
                if p.exists():
                    register(p);r['reviewed_hashes'][rel]=sources[str(p)]['sha256']==expected
        elif review.get('audited_task_success') is False and r.get('success'):
            r['termination_class']='native_success_rejected_by_task_audit'
        rows.append(r)
    report['tasks'][task]={'claimed':{'door':2,'bendpick':1}.get(task),
        'verified':sum(r['counted'] for r in rows),'completed_physical_attempts':sum(r.get('actions',0)>0 for r in rows),
        'completed_zero_action_records':sum(r.get('state')=='completed' and r.get('actions',0)==0 for r in rows),
        'continuing_episode_ids':[r['episode_id'] for r in rows if r['state']!='completed'],
        'termination_counts':dict(collections.Counter(r.get('termination_class','incomplete_at_snapshot') for r in rows)),
        'backend':'SIMPLE MuJoCo / SimpleLiveSim / checkpoint PD / ScaleBFM UMI-4',
        'episodes':rows}
report['tasks']['door']['qualification']='asset003 push-open variant, not original CloseDoor benchmark; closed reset/asset orientation adapted; exact-frame-four-boxes-v1 fixed-frame collision repair. Initial alignment differs among successes; no single-parameter causal claim. UUIDs/processes separate.'
report['tasks']['bendpick']['qualification']='One retained unsupported lift; native threshold trailing span 2.54s and unsupported last span17.3s. No separate full-height hold action or robustness test.'
representatives=[('R018/campaign','0001'),('R018/campaign','0437'),('R019/door-campaign','0008'),
    ('R019/door-campaign','0011'),('R019/bendpick-campaign','0006'),('R019/apple-campaign','0003'),
    ('R019/faucet-campaign','0005'),('R019/faucet-campaign','0006'),('R019/boxplace-campaign','0001'),('R019/boxplace-campaign','0002')]
for folder,eid in representatives:
    ep=ROOT/'artifacts'/folder/f'episode-{eid}'; raw=brief_result(ep/'result.json')
    item={'episode':str(ep),'result':raw,'video':video(ep/'video/episode.mp4')}
    for name in ['failure_review.json','infrastructure_review.json','evaluation.json']:
        if (ep/name).exists():item[name]=read(ep/name)
    p=ep/'rollout/history.jsonl'
    if p.exists():
        register(p); rows=[json.loads(s) for s in p.read_text().splitlines()]
        indexes=([58,59,60,64] if folder.endswith('apple-campaign') else [len(rows)-2,len(rows)-1])
        if folder.endswith('door-campaign') and eid=='0011':indexes=[18,19,28]
        item['selected_public_decisions']=[{'history_index':i,'tool':rows[i].get('tool'),
          'reason':rows[i].get('arguments',{}).get('response',{}).get('reason'),
          'native_outcome':rows[i].get('native_outcome')} for i in indexes if 0<=i<len(rows)]
    report['representative_public_decisions'].append(item)
api=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0001'
report['tasks']['api_floor_to_table']={'first_batch':brief_result(api/'result.json'),'video':video(api/'video/episode.mp4'),
    'verified_full_task_successes':0,'scope':'One human-feedback API learning attempt, six calls/three actions, batch truncated; no physical-failure credit. Approved120-call successor owned by rsi-aux-api-002-0916; not inspected/modified or assumed executed.'}
report['tasks']['floor_transfer_diagnostic']={'source':str(ROOT/'api-ground-to-table/transfers/original-table-locomotion-001/result.json'),
    'result':read(ROOT/'api-ground-to-table/transfers/original-table-locomotion-001/result.json'),
    'counts_as_new_learning_success':False,'actor_access':False}
for rel in ['human-feedback/experiments/H001/status.json','human-feedback/H001-user-feedback-004.json']:
    report.setdefault('human_feedback',{})[rel]=read(ROOT/rel)
for rel in ['AGENTS.md','ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md','ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md',
 'ref/ACCOUNT2_ROLE_SKILL_REVIEW.md','artifacts/R020/source-manifest.json','ITERATIONS.md',
 'skills/loco-manip-core/SKILL.md','skills/loco-manip-direct/SKILL.md','skills/loco-manip-simple/SKILL.md',
 'rsi/policy_harness.py','rsi/skill_learning.py','rsi/skill_transfer.py','rsi/task_skill.py',
 'tools/learn_grasp_skill.py','tools/learn_simple_task.py','tools/learn_door_skill.py','tools/audit_simple_campaigns.py',
 'tools/codex_direct_sim.py','rsi/simple_placement.py','codex-account-2/continuation/PROMPT.md',
 'GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md',
 'GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/teacher_context.md',
 'GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md',
 'ref/RoboRSI/roborsi/embodied/skills/base/open_hinged_door/libero/SKILL.md',
 'ref/RoboRSI/roborsi/agents/task_wiki.py']:
    register(ROOT/rel)
register(OUT/'source-thread-messages.json')
report['snapshot_finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(OUT/'status-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(OUT/'source-manifest.json').write_text(json.dumps({'snapshot_finished_utc':report['snapshot_finished_utc'],'sources':sources},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'tasks':{k:{key:v[key] for key in ['verified','physical_attempts','completed_physical_attempts','continuing_episode_ids'] if key in v} for k,v in report['tasks'].items()},'hashed_sources':len(sources),'finished':report['snapshot_finished_utc']},ensure_ascii=False))
