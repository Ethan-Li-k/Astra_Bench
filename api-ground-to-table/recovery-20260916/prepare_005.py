"""Prepare a new independent experiment, never a retry of unknown call004-43."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent;PREP=OUT/'episode005-preparation'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def create(p,v):
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
dest=ROOT/'artifacts/R021/api-ground-005';dest.mkdir(exist_ok=False)
(PREP/'before-code').mkdir(exist_ok=False)
for n in ('actor.py','history_bound.py'):shutil.copy2(ROOT/'api-ground-to-table/actor-adapter'/n,PREP/'before-code'/n)
old=ROOT/'artifacts/R021/api-ground-004/loco-manip-direct/SKILL.md';(dest/'loco-manip-direct').mkdir()
seed=old.read_text().split('\n\n')
lesson='Episode003 reached recovery targets with tilt15.82deg rising, then crossed25deg: arrival is not stable stance. Episode004 had three early ankle relocations with measured rise; opposing foot headings grew. Fifteen later changed actions stayed grounded despite tilt<14.4deg. Small low arcs, grounded yaw correction and wrist withdrawal did not restore walking. Next test preserve/correct heading during early measured raised-foot movement before opposing yaw accumulates; inspect actual feet, wrists and the full tilt tail after landing. Reject if heading control removes clearance or a direction-preserved stance still stalls. Empty-hand candidates prove no gait, grasp or loaded carry.'
seed=[lesson if x.startswith('Public episode0001 ended') else x for x in seed]
skill=dest/'loco-manip-direct/SKILL.md';skill.write_text('\n\n'.join(seed))
for src,name in [(PREP/'PLAN.md','reviewed-plan.md'),(OUT/'CONTINUE-AFTER-003.md','user-continuation-task.md'),
                 (OUT/'episode004-review/host-integrity.json','interruption004-audit.json'),
                 (OUT/'episode004-review/ledger-snapshot.json','prior-ledger-snapshot.json')]:shutil.copy2(src,dest/name)
transfer=json.loads((ROOT/'artifacts/R021/api-ground-004/public-transfer.json').read_text())
transfer.update(run_id='api-ground-005',episode='episode-0005')
review=json.loads((OUT/'episode004-review/review.json').read_text())
transfer['selected'].insert(0,dict(id='ground004-heading-before-stall-v1',status='public_counterexample_candidate',
    source=[x['source'] for x in review['observations']]+[x['source'] for x in review['traces']],
    mechanism='empty-hand support change and opposing foot heading',
    prerequisites='Same pinned original G1/DEX3/model38000/WristPI/table0; fresh reset and current cameras; actual foot rise and heading must be measured.',
    use='Early left/right/left feet moved118/101/131mm, peak rises39/44/42mm; left/right yaw grew from about-2/+1deg to-22/+13deg. Later changed attempts stayed grounded, including grounded yaw correction and withdrawal.',
    counterexample='Low tilt, target arrival, larger arc and hand withdrawal alone did not restore stepping.',
    different_test=review['next_distinguishing_test'],not_for='No loaded gait or success promotion; transfer interruption is not a physical failure.'))
transfer['notes']+=' Episode004 transport interrupted after19 actions; never replay its unknown43 or old002 unknown55. New observations/targets only.'
create(dest/'public-transfer.json',transfer)
b=json.loads((ROOT/'artifacts/R021/api-ground-004/batch.json').read_text());b.pop('approval')
b.update(batch_id='api-ground-005',episode='episode-0005',skill=ref(skill),public_transfer=ref(dest/'public-transfer.json'),
    direct_user_instruction=ref(dest/'user-continuation-task.md'),reviewed_plan=ref(dest/'reviewed-plan.md'),
    interruption004=ref(dest/'interruption004-audit.json'),prior_ledger_snapshot=ref(dest/'prior-ledger-snapshot.json'),
    authorization='User continuing task authorizes distinct reviewed independent resets under existing budget/normal execution approval. Not a retry or remote continuation of004-call43; unknown holds retained.')
spec=importlib.util.spec_from_file_location('binder005',ROOT/'ikea/budget-coordination/register_batch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=m.bind(b,[ref(ROOT/f'artifacts/R021/api-ground-00{i}/batch.json') for i in (1,2)])
create(dest/'approval.json',a);b['approval']=ref(dest/'approval.json');create(dest/'batch.json',b);m.b.reviewed_batch(ref(dest/'batch.json'))
auth=json.loads((ROOT/'api-ground-to-table/actor-adapter/authorization-004.json').read_text())
auth.update(run_id='api-ground-005',episode='episode-0005',batch=ref(dest/'batch.json'),approval=b['approval'],skill=b['skill'])
create(ROOT/'api-ground-to-table/actor-adapter/authorization-005.json',auth)
hook=(OUT/'recovery_budget004.py').read_text().replace('ground004_empirical_private','ground005_empirical_private').replace('api-ground-004','api-ground-005')
hook=hook.replace("PIN='3d0da8af3032b1735b9272798e33b3679e7cb3fa0504caba57631c0323603cac'",f"PIN='{ref(dest/'batch.json')['sha256']}'")
hook=hook.replace('OriginalLedger=budget.BudgetLedger',"PRIOR004=budget.load(budget.evidence(b['prior_ledger_snapshot']))\nINTERRUPTION004=budget.load(budget.evidence(b['interruption004']))\nOriginalLedger=budget.BudgetLedger")
needle="            approval=budget.parallel_approval(b)"
guard="""            key='api-ground-004-call-43'
            budget.require(state['requests'].get(key)==PRIOR004['requests'][key], 'Unknown004 request changed; review required')
            budget.evidence(INTERRUPTION004['result'])
            budget.evidence(PRIOR004['requests'][key]['completion_evidence'])
"""
hook=hook.replace(needle,guard+needle)
with (OUT/'recovery_budget005.py').open('x') as f:f.write(hook)
create(dest/'registration.json',dict(batch=ref(dest/'batch.json'),approval=b['approval'],ledger_mutated=False,dispatched=False,execution_review='pending',user_approved_this_schema=False))
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));import actor
text=skill.read_text()+'\n'+actor.INSTRUCTIONS
lengths=dict(words=len(text.split()),characters=len(text),nonwhitespace=len(''.join(text.split())))
assert lengths['words']<=831 and lengths['characters']<=6250 and lengths['nonwhitespace']<=5357,lengths
create(PREP/'skill-version.json',dict(previous=ref(old),current=ref(skill),lengths=lengths,public_review=ref(OUT/'episode004-review/review.json'),
    priority='GPT-as-Policy first; existing RoboRSI conditional lifecycle review second',shared_core_changed=False,physical_validation='pending'))
print(json.dumps(dict(batch=ref(dest/'batch.json'),lengths=lengths,requests_sent=0)))
