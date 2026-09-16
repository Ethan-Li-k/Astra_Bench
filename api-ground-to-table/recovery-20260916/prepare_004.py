"""Immutable new run metadata and short local skill; no request/ledger mutation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
PREP=OUT/'episode004-preparation'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(p,v):
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def main():
    dest=ROOT/'artifacts/R021/api-ground-004';dest.mkdir(exist_ok=False)
    (PREP/'before-code').mkdir(exist_ok=False)
    for name in ('actor.py','history_bound.py'):
        shutil.copy2(ROOT/'api-ground-to-table/actor-adapter'/name,PREP/'before-code'/name)
    old=ROOT/'artifacts/R021/api-ground-002/loco-manip-direct/SKILL.md'
    (dest/'loco-manip-direct').mkdir();new=dest/'loco-manip-direct/SKILL.md'
    paragraphs=old.read_text().split('\n\n')
    # Replace the verbose first-batch recap; retain its original source/version.
    paragraphs=[('Public episode0001 ended budget-limited after three actions; coordinated arcs moved feet, with posture/arm/amplitude confounded. Episode0003 stopped at tilt25.005deg. Its recovery reached targets but ended at tilt15.819deg and rising; the next swing aborted after0.44s with <1mm foot rise. Arrival is not stable stance. Test reduced landing/end-reference demand from a fresh measured stance; inspect the full pelvis-tilt tail and feet before another swing. Rising tilt requires a changed support/posture probe. These empty-hand candidates prove no gait, grasp or loaded carry.') if p.startswith('Public lessons from api episode0001:') else p for p in paragraphs]
    new.write_text('\n\n'.join(paragraphs))
    for src,name in [(OUT/'CONTINUE-AFTER-003.md','user-continuation-task.md'),(PREP/'PLAN.md','reviewed-plan.md')]:shutil.copy2(src,dest/name)
    v=json.loads((OUT/'public-transfer.json').read_text())
    v.update(run_id='api-ground-004',episode='episode-0004')
    # Immutable snapshot excerpts of public task memory, not a shared publication.
    snapshots={}
    for task,version in [('door',14),('boxplace',3)]:
        p=ROOT/f'artifacts/R019/{task}-campaign/memory/experience.jsonl'
        row=next(x for x in map(json.loads,p.read_text().splitlines()) if x.get('version')==version)
        snap=PREP/f'simple-{task}-v{version}.json';save(snap,row);snapshots[task]=ref(snap)
    v['selected']=[x for x in v['selected'] if x['id']!='simple-door0011-unload-reposition-v11']
    review=json.loads((OUT/'episode003-review/review.json').read_text())
    v['selected'].insert(0,dict(id='ground003-arrival-not-stability-v1',status='public_counterexample_candidate',
        source=review['public_sources'],mechanism='empty-hand landing and posture recovery',
        prerequisites='Same pinned G1/DEX3/model38000/WristPI/table0. Recheck fresh stance and public pelvis quaternion trend.',
        use=review['observed_trigger']+' '+review['facts'][0],different_test=review['next_test'],
        counterexample='A preceding right progression began at 4.11deg but ended23.82deg; initial low tilt alone is insufficient.',
        not_for='No causal controller/contact conclusion or verified grasp/carry gait; no human failure cluster.'))
    v['selected'].append(dict(id='simple-door0014-posture-recenter-v14',status='mechanism_hypothesis_only',source=[snapshots['door']],
        mechanism='wrist response changes with stance-relative arm placement',
        use='Public actions12/13/14/15 report failed raise with passive foot movement, then withdrawal/recentering and improved measured raise.',
        prerequisites='Source SimpleLiveSim body PD/corrected door asset is not proved identical to original-table WristPI; transfer observation method only.',
        different_test='Check measured wrist demand and support movement after each landing in this task.',
        not_for='No coordinates, success promotion, door mechanics, loaded locomotion or exact trajectory transfer.'))
    v['rejected']=[dict(id='simple-boxplace-v3',source=snapshots['boxplace'],reason='Budget-limited, no verified acquisition. Free-space descent and simultaneous ankle references undertracked; not a successful placement template.')]
    v['framework_selection']=[dict(source=ref(ROOT/f'artifacts/architecture-review-20260916/{p}'),use=use) for p,use in [
        ('HANDOFF-API.md','Use combined skill/runtime length validation only.'),
        ('memory-priority/INTEGRATION.md','Retain success eligibility; no qualified successful API task memory. Do not install incompatible shared module.'),
        ('no-truncation/INTEGRATION.md','ACK NT-v1; CodexRPC network patch incompatible with direct Responses API. Keep verified local no-tool completed continuation and fail closed on unknown requests.'),
        ('no-truncation/skills/ground/SKILL.md','Use conditional selection and natural-boundary rules; no wholesale second main skill.')]]
    save(dest/'public-transfer.json',v)
    b=json.loads((ROOT/'artifacts/R021/api-ground-003/batch.json').read_text());b.pop('approval')
    b.update(batch_id='api-ground-004',episode='episode-0004',
        authorization='User CONTINUE-AFTER-003 explicitly authorizes a fresh in-task attempt after review; normal execution approval remains separate.',
        direct_user_instruction=ref(dest/'user-continuation-task.md'),reviewed_plan=ref(dest/'reviewed-plan.md'),
        skill=ref(new),public_transfer=ref(dest/'public-transfer.json'))
    spec=importlib.util.spec_from_file_location('binder004',ROOT/'ikea/budget-coordination/register_batch.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a=m.bind(b,[ref(ROOT/f'artifacts/R021/api-ground-00{i}/batch.json') for i in (1,2)])
    save(dest/'approval.json',a);b['approval']=ref(dest/'approval.json');save(dest/'batch.json',b)
    m.b.reviewed_batch(ref(dest/'batch.json'))
    auth=json.loads((ROOT/'api-ground-to-table/actor-adapter/authorization-003.json').read_text())
    auth.update(run_id='api-ground-004',episode='episode-0004',batch=ref(dest/'batch.json'),approval=b['approval'],skill=b['skill'])
    save(ROOT/'api-ground-to-table/actor-adapter/authorization-004.json',auth)
    hook=(OUT/'recovery_budget.py').read_text().replace('ground003_empirical_private','ground004_empirical_private').replace('api-ground-003','api-ground-004')
    hook=hook.replace("PIN='492808c6703c18bf07c7a2469312a15d4a4ecf5640aaa957cd882b2d6d97dd65'",f"PIN='{ref(dest/'batch.json')['sha256']}'")
    with (OUT/'recovery_budget004.py').open('x') as f:f.write(hook)
    save(dest/'registration.json',dict(batch=ref(dest/'batch.json'),approval=b['approval'],ledger_mutated=False,dispatched=False,execution_review='pending',user_approved_this_schema=False))
    sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));import actor
    text=new.read_text()+'\n'+actor.INSTRUCTIONS
    lengths=dict(words=len(text.split()),characters=len(text),nonwhitespace=len(''.join(text.split())))
    assert lengths['words']<=831 and lengths['characters']<=6250 and lengths['nonwhitespace']<=5357,lengths
    save(PREP/'skill-version.json',dict(old=ref(old),new=ref(new),source_review=ref(OUT/'episode003-review/review.json'),
        lengths=lengths,pattern_priority=['GPT-as-Policy short task skill with external public experience','RoboRSI conditional lifecycle review'],
        status='task_local_candidate_not_physically_validated',shared_core_changed=False))
    print(json.dumps(dict(batch=ref(dest/'batch.json'),lengths=lengths,model_requests=0)))

if __name__=='__main__':main()
