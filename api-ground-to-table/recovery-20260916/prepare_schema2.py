"""Use the delivered schema2 binder in this branch's independent write domain."""
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
b=json.loads((OUT/'api-ground-003/batch.json').read_text());b.pop('approval')
b.update(schema=2,branch='api-ground-to-table',destination=b['provider']+'/v1/responses',data_scope='actor_public_rgb_robot_state_actions_skill',
    direct_user_instruction=ref(OUT/'TASK.md'),reviewed_plan=ref(OUT/'NEW-RUN-PLAN.md'))
out=OUT/'api-ground-003-reviewed';out.mkdir(exist_ok=False)
retained=[ref(ROOT/f'artifacts/R021/api-ground-00{i}/batch.json') for i in (1,2)]
a=m.bind(b,retained);save(out/'approval.json',a)
b['approval']=ref(out/'approval.json');save(out/'batch.json',b)
m.b.reviewed_batch(ref(out/'batch.json'))
auth=ROOT/'api-ground-to-table/actor-adapter/authorization-003.json'
shutil.copy2(auth,OUT/'api-ground-003/authorization-superseded.json')
v=json.loads(auth.read_text());v.update(batch=ref(out/'batch.json'),approval=b['approval']);save(auth,v)
save(out/'registration.json',dict(batch=ref(out/'batch.json'),approval=b['approval'],ledger_mutated=False,dispatched=False,execution_review='pending',supersedes_unexecuted_draft='api-ground-003'))
print(json.dumps(ref(out/'batch.json')))
