"""Create new authorization artifacts once from current task, never old approval."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=ROOT/'api-ground-to-table/recovery-20260916'
BATCH=OUT/'api-ground-003'
BATCH.mkdir(exist_ok=False)
def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
before=OUT/'before-code';before.mkdir(exist_ok=False)
for name in ('actor.py','history_bound.py'):
    shutil.copy2(ROOT/'api-ground-to-table/actor-adapter'/name,before/name)
old=json.loads((ROOT/'artifacts/R021/api-ground-002/batch.json').read_text())
batch={k:old[k] for k in ['schema','provider','model','reasoning_effort','calibration_request_id','calibration_input_bytes','calibration_output_tokens','calibration_body_basis','max_calls','max_payload_bytes','max_output_tokens','margin_multiplier','pricing_verified','hard_cost_bound','automatic_retries']}
batch.update(batch_id='api-ground-003',episode='episode-0003',authorization='Current user reboot recovery instruction authorizes fresh independent in-task attempts; normal execution approval still required.',
    new_observation_data_authorized=True,physical_budget_s=180,max_episode_steps=9000,
    recovery_ledger_snapshot=ref(OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json'),
    interruption_audit=ref(OUT/'interruption-audit.json'),prior_completed_batches=[],
    skill=old['skill'],scope='original-table ground cube locomotion grasp carry place only')
approval=dict(batch,approved=True,approval_kind='current_user_task_scope',direct_user_instruction_file=ref(OUT/'TASK.md'),
    reviewed_plan=ref(OUT/'NEW-RUN-PLAN.md'),destination=batch['provider']+'/v1/responses',single_independent_episode=True,
    execution_approval_status='pending_normal_tool_execution_review',prior_episode_approval_reused=False,
    allowed_data=['head/wrist simulation RGB','named robot proprioception and calibration','public actions and execution feedback','task-local skill and public experience summaries'])
save(BATCH/'approval.json',approval)
batch['approval']=ref(BATCH/'approval.json');save(BATCH/'batch.json',batch)
auth=dict(run_id='api-ground-003',episode='episode-0003',provider=batch['provider'],model='gpt-6-astra',effort='xhigh',
    new_simulation_images_approved=True,max_calls=120,batch=ref(BATCH/'batch.json'),approval=batch['approval'],skill=batch['skill'])
save(ROOT/'api-ground-to-table/actor-adapter/authorization-003.json',auth)
print(json.dumps(dict(batch=ref(BATCH/'batch.json'),approval=batch['approval'],authorization=ref(ROOT/'api-ground-to-table/actor-adapter/authorization-003.json')),indent=2))
