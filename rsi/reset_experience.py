"""Per-reset frozen examples: one relevant audited success and one counterexample."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def build_bundle(public,env_id,task,labels,sources,preferred=()):
    public=Path(public);index=json.loads((public/'atomic-index.json').read_text())
    aliases={'open_enclosure':'enclosure','closure':'enclosure','probe_lift':'retention','separate_hold':'retention','acquire':'enclosure','hold':'retention','transport':'loaded_travel'}
    def phases(values):return {aliases.get(v,v) for v in values}-{'approach','support','tracking'}
    wanted=phases(task['source_phases'])
    def applicable(row):
        if row['env_id']==env_id:return True
        if not wanted.intersection(phases(row['phases'])):return False
        grasp=set((labels or {}).get('grasp',[]))-{'any','interface_probe'}
        source_grasp=set(row.get('selection',{}).get('grasp',[]))
        return not grasp or not source_grasp or 'any' in source_grasp or bool(grasp & source_grasp)
    def rank(row):
        shape=sum(len(set(v)&set(row.get('selection',{}).get(k,[]))) for k,v in (labels or {}).items())
        return (row['env_id']!=env_id,row['id'] not in preferred,-shape,row['control_contract']!=task.get('source_control_contract',index['control_contract']),row['id'])
    available=[r for r in index['sources'] if applicable(r)];chosen=[]
    for category in ('audited_source','counterexample'):
        candidates=[r for r in available if r['status']==category]
        if candidates:chosen.append(min(candidates,key=rank))
    cases=[]
    fields=('id','env_id','status','principle','observed','preconditions','exit_evidence','when_not_to_use','completion_contract','human_feedback_used','human_demonstration_used')
    for row in chosen:
        path=public/row['path'];raw=path.read_bytes();atom=json.loads(raw);same=row['control_contract']==task.get('source_control_contract',index['control_contract'])
        case={k:atom[k] for k in fields if k in atom};case.update(source_path=str(path.resolve()),source_sha256=hashlib.sha256(raw).hexdigest(),transfer_mode='same_controller_revalidate_current_scene' if same else 'semantic_phases_only_no_pose_gain_or_motion_replay')
        # Obsolete campaign attempt limits are management history, not reusable geometry.
        if 'when_not_to_use' in case:case['when_not_to_use']=case['when_not_to_use'].replace('No further repetition if this final corrected attempt is incomplete.','')
        cases.append(case)
        sources[row['id']]={'path':str(path.resolve()),'sha256':case['source_sha256'],'scope':'published_success_or_counterexample','applicability':case.get('preconditions',''),'when_not_to_use':case.get('when_not_to_use',''),'transfer_mode':case['transfer_mode']}
    archive=ROOT/'artifacts/harness-reset-20260917/execution/experience'/(hashlib.sha256(env_id.encode()).hexdigest()+'.jsonl')
    if archive.exists():
        latest=json.loads(archive.read_text().splitlines()[-1]);path=Path(latest['path']);value=json.loads(path.read_text())
        case=dict(value,id='recent-self-'+value['episode_id'],status='self_report_not_audited',source_path=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),transfer_mode='recompute_current_scene_no_coordinate_replay')
        # A newly promoted atom already embeds this exact complete public lesson.
        # Retain it once, with its pinned original file in public_evidence.
        duplicate = any(c.get('observed') == value for c in cases)
        if not duplicate:
            cases.append(case);sources[case['id']]={'path':str(path),'sha256':case['source_sha256'],'scope':'frozen_public_self_lesson','applicability':'Recent same-task self-observed failure/success hypothesis, not audited geometry','when_not_to_use':'No old world target or hidden state replay'}
    return {'id':'success-failure-reset-icl-v1','cases':cases,'required_selection_groups':[[x['id'] for x in cases if x['status']==s] for s in ('audited_source','counterexample')],'missing_compatible_categories':[category for category in ('audited_source','counterexample') if not any(r['status']==category for r in chosen)],'selection_rule':'Applicable phase/mechanism before ranking; absent compatible case is explicitly missing, never force an unrelated example','historical_outcomes_do_not_count_as_new_attempts':True}


def record_selection(host,arguments):
    groups=getattr(host,'required_experience_groups',[])
    if any(group and not set(group)&set(arguments['selected_ids']) for group in groups):
        raise ValueError('Select one supplied success and one counterexample; explain adaptation and rejected details')


def save_lesson(host,arguments):
    config=getattr(host,'attempt_progress_config',None)
    if not config:return
    value={'env_id':config['env_id'],'episode_id':host.episode_id,'source_episode':str(host.output),
        'lesson':arguments['lesson'],'change_summary':arguments.get('change_summary'),
        'source_access':'This frozen public lesson only; original episode paths are provenance, not read permission',
        'actor_claim_not_audit':True}
    path=Path(host.output)/'public-lesson.json';path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    folder=ROOT/'artifacts/harness-reset-20260917/execution/experience';folder.mkdir(exist_ok=True)
    archive=folder/(hashlib.sha256(config['env_id'].encode()).hexdigest()+'.jsonl')
    with archive.open('a') as f:f.write(json.dumps({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})+'\n')
