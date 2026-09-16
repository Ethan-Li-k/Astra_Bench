"""Read actual handshake and first-action receipts; no model/physics invocation."""
from pathlib import Path
import argparse,datetime,hashlib,json
p=argparse.ArgumentParser();p.add_argument('episode',type=Path);a=p.parse_args();ep=a.episode.resolve()
read=lambda s:json.loads((ep/s).read_text())
backend=read('model_backend.json');assert backend['account_route']=='authorized_account_2' and backend['fallback'] is False
assert backend['launcher']=='/home/galbot/lizekai/RSI/codex-account-2/run.sh'
sent=[json.loads(s) for s in (ep/'app_server/rpc_in.jsonl').read_text().splitlines()]
received=[json.loads(s) for s in (ep/'app_server/rpc_out.jsonl').read_text().splitlines()]
start=next(x for x in sent if x.get('method')=='thread/start');params=start['params']
answer=next(x['result'] for x in received if x.get('id')==start['id'])
init=next(x for x in sent if x.get('method')=='initialize');home=next(x['result']['codexHome'] for x in received if x.get('id')==init['id'])
assert home=='/home/galbot/lizekai/RSI/codex-account-2/home'
assert params['model']==answer['model']=='gpt-6-astra' and params['config']['model_reasoning_effort']==answer['reasoningEffort']=='xhigh'
assert params['allowProviderModelFallback'] is False
assert params['sandbox']=='workspace-write' and answer['sandbox']['type']=='workspaceWrite' and answer['sandbox']['networkAccess'] is False
assert answer['approvalPolicy']==params['approvalPolicy']=='on-request' and answer['approvalsReviewer']==params['approvalsReviewer']=='auto_review'
assert answer['runtimeWorkspaceRoots']==params['runtimeWorkspaceRoots']==[str(ep/'agent')]
text=params['developerInstructions'];budget=read('policy_instruction_budget.json');digest=hashlib.sha256(text.encode()).hexdigest()
assert digest==budget.get('developer_instructions_sha256',budget['combined_sha256'])
reserved=text+budget.get('network_continuation','');size=lambda s:dict(words=len(s.split()),characters=len(s),non_whitespace=len(''.join(s.split())))
assert size(reserved)==budget['combined_size']
assert all(size(reserved)[k]<=limit for k,limit in budget['caps'].items())
rows=[json.loads(s) for s in (ep/'rollout/history.jsonl').read_text().splitlines()]
actions=[x for x in rows if x['tool']=='scalebfm_act'];assert actions and actions[0]['execution']
scene=read('video/scene_setup.json');reset=scene['reset_provenance'];assert reset['method']=='fresh_environment_reset'
obs=read('rollout/episode/observations/0000/observation.json')
assert all(x['calibration']['render_intrinsics']['version']=='mujoco-render-frustum-v1' for x in obs['images'])
record=dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),model=answer['model'],effort=answer['reasoningEffort'],codex_home=home,thread_id=answer['thread']['id'],launcher=backend['launcher'],fallback=False,first_physical_action_observed=True,observed_actions=len(actions),reset_id=reset['reset_id'],reset_seed=reset['seed'],boot_id=reset['launch']['boot_id'],actual_sent_combined_size=size(text),reserved_combined_size=size(reserved),actual_sent_instructions_sha256=digest,sandbox=answer['sandbox'],runtimeWorkspaceRoots=answer['runtimeWorkspaceRoots'],approvalPolicy=answer['approvalPolicy'],approvalsReviewer=answer['approvalsReviewer'],render_intrinsics_version='mujoco-render-frustum-v1')
path=ep/'account_route_verified.json';assert not path.exists();path.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
