"""Register metadata within the shared ledger's existing evidence allowlist."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('schema2_binder',ROOT/'ikea/budget-coordination/register_batch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=ROOT/'artifacts/R021/api-ground-003';out.mkdir(exist_ok=False)
for src,name in [(OUT/'TASK.md','user-recovery-task.md'),(OUT/'NEW-RUN-PLAN.md','reviewed-plan.md'),
                 (OUT/'interruption-audit.json','interruption-audit.json'),
                 (OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json','old-ledger-audit-snapshot.json')]:
    shutil.copy2(src,out/name)
b=json.loads((OUT/'api-ground-003/batch.json').read_text());b.pop('approval')
b.update(schema=2,branch='api-ground-to-table',destination=b['provider']+'/v1/responses',data_scope='actor_public_rgb_robot_state_actions_skill',
    direct_user_instruction=ref(out/'user-recovery-task.md'),reviewed_plan=ref(out/'reviewed-plan.md'),
    recovery_ledger_snapshot=ref(out/'old-ledger-audit-snapshot.json'),interruption_audit=ref(out/'interruption-audit.json'))
a=m.bind(b,[ref(ROOT/f'artifacts/R021/api-ground-00{i}/batch.json') for i in (1,2)])
save(out/'approval.json',a);b['approval']=ref(out/'approval.json');save(out/'batch.json',b)
m.b.reviewed_batch(ref(out/'batch.json'))
auth=ROOT/'api-ground-to-table/actor-adapter/authorization-003.json'
shutil.copy2(auth,OUT/'api-ground-003/authorization-superseded.json')
v=json.loads(auth.read_text());v.update(batch=ref(out/'batch.json'),approval=b['approval']);save(auth,v)
receipt=dict(batch=ref(out/'batch.json'),approval=b['approval'],ledger_mutated=False,dispatched=False,execution_review='pending',supersedes_unexecuted_drafts=['api-ground-003','api-ground-003-reviewed'])
save(out/'registration.json',receipt);save(OUT/'schema2-registration.json',receipt)
print(json.dumps(receipt,indent=2))
