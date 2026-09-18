"""Supervisor recovery for old API workers lacking an in-process route hook.

An ended delivery is not proof of a remote terminal. Fence the old executor,
retain the unknown request, and start an explicitly distinct authorized reset.
"""
import hashlib,json,os,re,shutil,signal,subprocess,time
from pathlib import Path

R=Path('/home/galbot/lizekai/RSI');B=R/'artifacts/six-transfer-20260917'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
    from rsi.actor_transport import atomic
    atomic(p,v)


def eligibility(episode):
    ep=Path(episode);p=ep/'api-service-paused.json'
    if not p.exists() or (ep/'api-main-handoff.json').exists():return None
    pause=read(p)
    if pause.get('status')!='service_paused_live_scene_retained':return None
    error=pause.get('error','')
    if not (error.startswith('missing_terminal_response;')
            or re.fullmatch(r'HTTP (400|401|402|403|404|413|422|429); no retry; expense unknown',error)):
        return None
    receipts=sorted((ep/'api-continuation').glob('*/calls/*/receipt.json'),key=lambda p:read(p).get('started_at_unix',0))
    if not receipts:return None
    row=read(receipts[-1]);blocked=read(ep/'api-continuation/blocked.json')
    if (row.get('state')!='unknown_no_retry' or row.get('response_id') or not row.get('finished_at_unix')
            or blocked.get('reset_id')!=pause.get('reset_id')):return None
    # Original background handles take the existing GET recovery path instead.
    if any(read(p).get('original_response_id') for p in (ep/'background-requests').glob('*.json')):return None
    if any(read(p).get('state')!='completed' for p in receipts[:-1]):return None
    actions=list((ep/'api-continuation/actions').glob('*.json'))
    if any(read(p).get('status')!='completed' for p in actions):return None
    return dict(request_receipt=str(receipts[-1]),request_receipt_sha256=sha(receipts[-1]),
        request_sha256=row['request_sha256'],stream_closed_at=row['finished_at_unix'],
        reset_id=pause['reset_id'],physical_actions_confirmed=pause['actions'],
        completed_tool_receipts=len(actions),unknown_output_dispatched=False,
        classification='api_http_429' if error.startswith('HTTP 429;') else 'api_delivery_interrupted',
        remote_result='unknown_preserved_no_repost')


def recover_if_eligible(env_id,item):
    ep=Path(item['episode']);pid=item['process'].pid;fpath=ep/'execution-fence.json'
    if not fpath.exists():
        boundary=eligibility(ep)
        if boundary is None:return None
        cmd=Path('/proc',str(pid),'cmdline')
        if not cmd.exists() or env_id.encode() not in cmd.read_bytes():return None
        row=dict(boundary,status='fencing_requested',at=time.time(),pid=pid,
            authority='User-authorized execution-fenced new-reset main recovery',
            physical_failure=False,complete_attempt=False)
        write(fpath,row)
        os.kill(pid,signal.SIGINT)  # finally closes video; no pending API/action.
        return {'status':'fencing_requested'}
    row=read(fpath)
    if row['status']=='execution_fenced':return None
    if row['status']!='fencing_requested':return None
    if item['process'].poll() is None:return {'status':'waiting_executor_close'}
    if Path('/proc',str(pid)).exists():return {'status':'waiting_executor_close'}
    # Closed video confirms orderly cleanup. Never overwrite or delete evidence.
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(ep/'video/episode.mp4')],capture_output=True,text=True)
    if probe.returncode or float(json.loads(probe.stdout).get('format',{}).get('duration',0))<=0:
        return {'status':'waiting_video_seal'}
    row.update(status='execution_fenced',execution_fenced_at=time.time(),old_process_absent=True,
               late_output_cannot_execute=True,video_sealed=True,video_sha256=sha(ep/'video/episode.mp4'))
    write(fpath,row)
    write(ep/'infrastructure_review.json',dict(termination_class='infrastructure_interruption',
        reason=row['classification'],execution_fence=str(fpath),task_failure=False,complete_attempt=False))
    return publish_main_recovery(env_id,ep)


def publish_main_recovery(env_id,ep):
    from rsi.main_account import MAIN_ONLY_POLICY,require_main_source
    from rsi.skill_release import AUTHOR,publish_release,runtime_instructions,task_snapshot
    from rsi.frozen_skill import file_hashes
    require_main_source()
    fence=read(ep/'execution-fence.json')
    if fence['status']!='execution_fenced' or Path('/proc',str(fence['pid'])).exists():
        raise ValueError('Old execution must be fenced first')
    notes=ep/'agent/NOTES.md'
    originals=[notes,*sorted((ep/'api-continuation').glob('public-exchange-*.json'))]
    write(ep/'confirmed-public-evidence-index.json',dict(excludes_unknown_response=True,
        files=[{'path':str(p),'sha256':sha(p)} for p in originals if p.exists()]))
    lp=ep/'public-lesson.json'
    if not lp.exists():
        write(lp,dict(env_id=env_id,episode_id=ep.name,source_episode=str(ep),
            lesson=notes.read_text() if notes.exists() else 'No public note before transport interruption.',
            change_summary='Transport interruption; original confirmed public experience remains unchanged. Recompute from the new reset, never replay old coordinates.',
            termination_class='transport_interrupted',actor_claim_not_audit=True,
            source_access='Verbatim original notes; confirmed original exchanges are preserved separately.',
            original_public_evidence_index={'path':str(ep/'confirmed-public-evidence-index.json'),'sha256':sha(ep/'confirmed-public-evidence-index.json')}))
        archive=R/'artifacts/harness-reset-20260917/execution/experience'/(hashlib.sha256(env_id.encode()).hexdigest()+'.jsonl')
        with archive.open('a') as f:f.write(json.dumps({'path':str(lp),'sha256':sha(lp)})+'\n')
    global_ptr=read(R/'skills/releases/CURRENT.json');rs=R/'skills/transport-releases'
    previous=read(rs/'CURRENT.json');rid='central-20260917-main-'+hashlib.sha256(str(ep).encode()).hexdigest()[:10]
    draft=B/'legacy-main-recovery'/('draft-'+rid)
    if draft.exists():raise ValueError('Interrupted publication requires review; never overwrite')
    shutil.copytree(R/'skills/releases'/global_ptr['release_id'],draft)
    m=read(draft/'release.json');m['tasks']={env_id:m['tasks'][env_id]};t=m['tasks'][env_id]
    sp=draft/'public'/t['task_spec_path'];spec=read(sp);spec['actor_backend_policy']=MAIN_ONLY_POLICY;spec.pop('direct_api',None)
    spec['transport_recovery']=dict(mode='new_reset_after_transport',source_episode=str(ep),
        source_reset_id=fence['reset_id'],old_request_state='unknown_execution_fenced',no_request_or_action_replay=True)
    write(sp,spec);t['bindings'].pop('direct_api',None);t['bindings'].pop('api_background',None)
    t['bindings'].update(main_account=True,task_spec_sha256=sha(sp))
    role=R/'main-account/home/AGENTS.md';snap=task_snapshot(draft/'public',t)
    write(snap/'ambient-instructions.json',{str(role):sha(role)});(snap/'ROLE_CONTRACT.md').write_bytes(role.read_bytes())
    old='Submit evidence-backed task or shared skill proposals; the manager alone publishes for new resets. Preserve human-assistance labels and use only permitted observations.'
    skill=snap/'SKILL.md';skill.write_text(skill.read_text().replace(old,'Submit evidenced updates for next resets; keep feedback labels.').replace('Use supplied workspace, task and CONTROL.', 'Read workspace, task and CONTROL.'))
    runner=R/'tools/learn_simple_task.py'
    m['runtime_code_hashes'][str(runner.relative_to(R))]=sha(runner)
    m.update(release_id=rid,status='draft',actor_backend_policy=MAIN_ONLY_POLICY,
        parent_publication_sha256=global_ptr['manifest_sha256'],
        change_note='Explicit main-account NEW reset after old transport execution fence; original unknown request is never replayed.')
    m['public_hashes']=file_hashes(draft/'public');write(draft/'release.json',m)
    ptr=publish_release(draft,rs,rid,author=AUTHOR,expected_previous=previous['manifest_sha256'],
        runtime=runtime_instructions(R/'tools/learn_grasp_skill.py',R/'rsi/codex_app_server.py'))
    override=dict(env_id=env_id,route='main_chatgpt',release_path=str(rs/rid),release=ptr,
        runner=str(runner),fenced_episode=str(ep),execution_fence_sha256=sha(ep/'execution-fence.json'),
        mode='new_reset_after_transport',model='gpt-6-astra',effort='xhigh')
    path=B/'execution/route-overrides.json';overrides=read(path) if path.exists() else {}
    overrides[env_id]=override;write(path,overrides)
    write(ep/'new-reset-main-recovery.json',dict(status='ready_to_dispatch',override=override,
        original_notes_verbatim=True,old_request_reposted=False,old_actions_replayed=False))
    return override
