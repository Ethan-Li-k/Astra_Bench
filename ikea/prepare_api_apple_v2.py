"""Prepare a future isolated caller; no registration, model, or physics launch."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('Unexpected source fragment: '+old[:80])
    return text.replace(old,new,1)


def main():
    src=ROOT/'api-apple-v1';out=ROOT/'api-apple-v2';out.mkdir(exist_ok=False)
    frozen=ROOT/'runtime-apple-v2';shutil.copytree(ROOT/'runtime-apple-v1',frozen)
    # Keep identical frozen controller/tool code; replace only the declared reset.
    backend=(ROOT/'apple_backend_close_reset_v2.py').read_text()
    backend=backend.replace('import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent/"runtime-apple-v1"))\n','',1)
    (frozen/'apple_backend.py').write_text(backend)
    hashes=json.loads((frozen/'manifest.json').read_text())
    for rel in hashes:hashes[rel]=hashlib.sha256((frozen/rel).read_bytes()).hexdigest()
    (frozen/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    support=(ROOT/'policy_support_apple_v1.py').read_text().split('\ndef main():')[0]+'\n'
    support=support.replace("ROOT/'runtime-apple-v1'","ROOT/'runtime-apple-v2'")
    support=support.replace('This uses the original IKEA apple geometry/pose','Robot reset is0.25m closer than apple-0001; no approach-from-the-old-start credit. This uses the original IKEA apple geometry/pose')
    (ROOT/'policy_support_apple_v2.py').write_text(support)
    for name in ('history_bound.py','budget_hook.py','test_local_adapter.py'):
        shutil.copy2(src/name,out/name)
    gate=(src/'transport_gate.py').read_text()
    gate=replace_once(gate,"if type(max_calls) is not int or max_calls not in (6, 120):\n            raise ValueError('Unregistered call allowance')\n        if max_calls == 120 and run_id != 'api-ikea-apple-001':\n            raise ValueError('120 calls belong only to registered api-ikea-apple-001')", "if type(max_calls) is not int or not 1 <= max_calls <= 120:\n            raise ValueError('Unregistered call allowance')\n        batch = budget.batch\n        if run_id != batch['batch_id'] or max_calls != batch['max_calls']:\n            raise ValueError('Session must match its exact registered batch')")
    (out/'transport_gate.py').write_text(gate)
    hook=(out/'budget_hook.py').read_text().replace("environment='isolated-IKEA-MuJoCo-original-apple-convex-018kg-v1'","environment=batch['environment_variant']")
    (out/'budget_hook.py').write_text(hook)
    runner=(src/'run_api_policy.py').read_text().replace('policy_support_apple_v1','policy_support_apple_v2')
    runner=runner.replace("RUN='api-ikea-apple-001'","RUN='api-ikea-apple-002'\nfrom serial_batch_continuation import SerialBatchContinuation")
    runner=runner.replace("'source-aligned-apple-convex-0.18kg-v1'","'source-aligned-apple-convex-close-robot-v2'")
    runner=replace_once(runner,'def register(output,skill):','def register(output,skill,run_id,episode,previous=None):')
    runner=runner.replace('batch_id=RUN,purpose=', 'batch_id=run_id,purpose=')
    runner=replace_once(runner,"'Fresh independent IKEA original tabletop apple grasp; no old request replay'", "'IKEA apple physical episode; exact scoped serial batch, no old request replay'")
    runner=replace_once(runner,'episode=output.name,episode_output=str(output),',"episode=episode,episode_output=str(ROOT/'campaign'/episode),\n        environment_variant='isolated-IKEA-MuJoCo-apple-close-robot-v2',previous_completed_batch=previous,")
    runner=runner.replace("'--name',RUN","'--name',run_id").replace("/'budget-coordination/approvals'/RUN/'registration.json'","/'budget-coordination/approvals'/run_id/'registration.json'")
    runner=replace_once(runner,"default='apple-0001'","default='apple-0002'")
    runner=replace_once(runner,"    campaign=ROOT/'campaign';campaign.mkdir(exist_ok=True)","    ready=Path(__file__).parent/'READY.json'\n    if not ready.exists():raise RuntimeError('Candidate not activated: finish prior episode review and preflight first')\n    approved=json.loads(ready.read_text())\n    if approved.get('ready') is not True:raise RuntimeError('Candidate not ready')\n    for name,digest in approved['source_sha256'].items():\n        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Activation source drift: '+name)\n    campaign=ROOT/'campaign';campaign.mkdir(exist_ok=True)")
    runner=runner.replace("ROOT/'skills/apple-grasp-v1/SKILL.md'","ROOT/'skills/apple-grasp-v2/SKILL.md'")
    runner=replace_once(runner,"ROOT/'policy_support_apple_v2.py']","ROOT/'policy_support_apple_v2.py',ROOT/'serial_batch_continuation.py']")
    runner=replace_once(runner,'    registration=register(output,skill);budget=RegisteredBudget(registration)',"    batch_root=output/'api-batches'/RUN;batch_root.mkdir(parents=True)\n    registration=register(batch_root,skill,RUN,args.episode);budget=RegisteredBudget(registration)\n    shutil.copy2(batch_root/'batch-terms.json',output/'batch-terms.json')")
    runner=replace_once(runner,"calls_available=120","calls_per_registered_batch=120,continuation='Completed responses may continue this same physical reset in a fresh registered batch; global shared budget still applies'")
    runner=replace_once(runner,'    session=None;gate=None;error=None;started=time.monotonic()',"    session=None;gate=None;error=None;started=time.monotonic();sessions=[];global_calls=0\n    flat_calls=output/'api-calls';flat_calls.mkdir()\n    def next_session(previous):\n        new_run=f'{RUN}-b{len(sessions)+1:02d}'\n        folder=output/'api-batches'/new_run;folder.mkdir()\n        reg=register(folder,skill,new_run,args.episode,previous)\n        new_budget=RegisteredBudget(reg)\n        new=ResponsesSession(folder/'calls',new_budget,HTTPSResponses(),new_run,max_calls=new_budget.batch['max_calls'])\n        sessions.append(new)\n        return new")
    runner=replace_once(runner,"        session=ResponsesSession(output/'api-calls',budget,HTTPSResponses(),RUN,max_calls=120)\n        # Natural model responses continue this same simulation. Only the explicitly registered call budget bounds dispatches.\n        while session.count<session.max_calls and not gate.concluded:","        session=ResponsesSession(batch_root/'calls',budget,HTTPSResponses(),RUN,max_calls=budget.batch['max_calls'])\n        sessions.append(session)\n        bridge=SerialBatchContinuation(session,host,next_session,output/'serial-batch-transitions.jsonl')\n        # No local call-count loop termination. Same host/history across completed batches.\n        while not gate.concluded:\n            session=bridge.ready(phase='terminal_review' if host.finished else 'policy')")
    runner=replace_once(runner,'            response=session.call(payload)',"            before_count=session.count\n            try:\n                response=session.call(payload)\n            finally:\n                if session.count>before_count:\n                    global_calls+=1\n                    source_call=session.output/f'{session.count:02d}'\n                    if source_call.exists():(flat_calls/f'{global_calls:02d}').symlink_to(source_call,target_is_directory=True)\n                    with (output/'api-call-series.jsonl').open('a') as stream:\n                        stream.write(json.dumps(dict(global_call=global_calls,run_id=session.run_id,batch_call=session.count,source=str(source_call)))+'\\n')")
    runner=runner.replace("packet['api_calls_remaining']=session.max_calls-session.count","packet['current_batch_calls_remaining']=session.max_calls-session.count\n            packet['same_episode_continuation']='A completed batch may be replaced through the unchanged shared budget; no reset or action replay.'")
    runner=runner.replace("f'public_tool_{session.count:04d}.json'","f'public_tool_{global_calls:04d}.json'")
    runner=replace_once(runner,"        if not host.finished:host.stop_reason='registered_api_call_budget'\n",'')
    runner=runner.replace("api_calls=session.count if session else 0,skill_updated=", "api_calls=sum(s.count for s in sessions),api_runs=[s.run_id for s in sessions],same_episode_serial_batches=True,skill_updated=")
    (out/'run_api_policy.py').write_text(runner)
    (out/'CANDIDATE.json').write_text(json.dumps(dict(status='prepared_not_activated',production_requests=0,
        pending=['Finish/review apple-0001; prepare evidence-backed next skill and length/updater preflight.',
                 'Update local transport tests for exact batch binding and test caller serial flow.',
                 'Adapt independent episode reviewer for per-batch receipt indexing and registration provenance.',
                 'Create hash-bound READY.json only after all preflight checks.'],
        source='Copied immutable v1; changes only in new v2 paths',reset='Declared closer-robot variant; no current episode reset'),indent=2)+'\n')
    print(json.dumps(dict(adapter=str(out),runtime=str(frozen),activated=False,paid_calls=0)))


if __name__=='__main__':main()
