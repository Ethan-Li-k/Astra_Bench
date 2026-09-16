from pathlib import Path
import json,hashlib,datetime,collections
B=Path(__file__).resolve().parent;R=Path('/home/galbot/lizekai/RSI');now=datetime.datetime.now(datetime.timezone.utc).isoformat();sources=[]
def read(rel):
 p=R/rel;data=p.read_bytes();sources.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)});return json.loads(data)
def public_snapshot(rel,name,keys=None):
 d=read(rel);v={k:d.get(k) for k in keys} if keys else d
 (B/'evidence'/name).write_text(json.dumps(v,ensure_ascii=False,indent=2));return v
out=[]
for campaign,episode in [('apple','0007'),('boxplace','0003'),('faucet','0007')]:
 p=f'artifacts/R019/{campaign}-campaign/episode-{episode}'
 d=read(p+'/result.json');selected={k:d.get(k) for k in ('episode_id','native_outcome','stop_reason','error','actions','sim_s','codex_turns','human_feedback_used','completion_contract')}
 turns=[]
 for q in sorted((R/p).glob('turn_*.json')):
  t=read(str(q.relative_to(R)));turns.append({'id':t.get('id'),'status':t.get('status')})
 out.append(dict(task=campaign,classification='physical_budget_incomplete',result=selected,turns=turns,source=p+'/result.json'))
p=R/'artifacts/R019/door-campaign/episode-0015/app_server/rpc_out.jsonl';counts=collections.Counter();errors=[]
with p.open() as f:
 for line in f:
  try:d=json.loads(line)
  except ValueError:continue
  method=d.get('method');counts[method]+=1
  if method=='error':
   e=d.get('params',{});errors.append({k:e.get(k) for k in ('threadId','turnId','willRetry','error')})
sources.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
setup=read('artifacts/R019/door-campaign/episode-0015/video/scene_setup.json')
reset=setup.get('reset_provenance',{})
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
out.append(dict(task='door',episode='0015',classification='host_restart_after_network_notifications_without_terminal',event_counts={k:counts[k] for k in ('turn/started','turn/completed','error','item/tool/call')},errors=errors,reset_provenance=reset,current_boot_id=boot,boot_changed=reset.get('boot_id')!=boot,remote_turn_terminal='unknown; no recovery permitted from notifications alone'))
api=public_snapshot('api-ground-to-table/actor-adapter/auxiliary-progress.json','api-public-status-snapshot.json')
provenance=read('api-ground-to-table/actor-adapter/campaign/episode-0002/provenance.json')
receipts=[]
for n in (53,54,55):
 p=R/f'api-ground-to-table/actor-adapter/campaign/episode-0002/api_calls/{n}/receipt.json';raw=p.read_bytes();sources.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
 d=json.loads(raw) if raw else {};receipts.append({'call':n,'bytes':len(raw),'metadata':{k:d.get(k) for k in ('state','response_status','response_id','model','effort','request_index','error_type','max_output_tokens')}})
out.append(dict(task='API-ground',episode='0002',classification='host_restart_unknown_request55_no_replay',public_status=api,representative_receipts=receipts,authorized_call_limit=provenance['max_calls'],human_feedback_used=provenance['human_feedback_used'],counts_caveat='54 completed / 23 actions are last published counters; final action evidence partly zero-length, not a complete audited action denominator'))
ikea=public_snapshot('ikea/state.json','ikea-state-snapshot.json',('updated_at','state','phase','thread_id','backend','model','reasoning_effort','actor_running','physical_attempts','audited_successes','system_interruption','diagnostic_runs','diagnostic_sim_s'))
incident=public_snapshot('ikea/recovery-20260916/incident.json','restart-incident.json')
out.append(dict(task='IKEA',classification='infrastructure_restart_then_owner_pre_actor_diagnostics',status=ikea,actor_completed_or_incomplete_turn='not applicable: no actor physical attempts in this snapshot',static_or_diagnostic_not_success=True))
ack=public_snapshot('artifacts/R019/instruction-cap-integration/ack.json','simple-first-review-ack.json')
(B/'evidence/outcomes.json').write_text(json.dumps(dict(snapshot_utc=now,scope='recent representative receipts; not a new success census',outcomes=out,classification_rules={'natural_end':'matching completed model turn; caller continues if task unfinished','active_wait':'same live process, no terminal; silence alone never proves stop','network_notification':'error/willRetry is not closure','network_closed':'matching failed terminal required for candidate recovery','EOF_or_RPC_unknown':'no new request; preserve ambiguity','model_incomplete_or_cap':'no demonstrated recent case here; API actor rejects non-completed status, not safe to relabel network','policy_stall':'finish_attempt already nonterminal; historical faucet27 completed turns was fault behavior, not 27 trials','wallclock_cancel':'not demonstrated in selected recent receipts; turn/start finite ACK wait is reproduced code exposure only','physical_budget':'SIMPLE 240-second boundary retained as incomplete','authorization':'API120 calls and shared10000RMB remain real boundaries; no quota/ledger inquiry performed','host_restart':'boot change proves lost local process continuity; no claim that remote request55 failed or was unbilled'}),ensure_ascii=False,indent=2))
refs=['ref/GPT-as-Policy/hybrid_rollout/robodojo/skill/'+n for n in ('run.py','network_recovery.py','transport.py')]+['ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/'+n for n in ('SKILL.md','context/teacher_context.md','context/eef_control.md')]
refs+=['skills/loco-manip-core/SKILL.md','skills/loco-manip-simple/SKILL.md','artifacts/R021/api-ground-002/loco-manip-direct/SKILL.md','artifacts/architecture-review-20260916/REVIEW.md','artifacts/R019/FRAMEWORK_OUTBOX.md','api-ground-to-table/recovery-20260916/RECOVERY.md','ref/USER_UPDATE_20260916_NO_TRUNCATION_SHARED_SKILLS.md']
for rel in refs:
 p=R/rel;sources.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
(B/'source-manifest.json').write_text(json.dumps({'snapshot_utc':now,'sources':sources,'secondary_reference':'RoboRSI: reuse first review findings; no new general reread'},ensure_ascii=False,indent=2))
