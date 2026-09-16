import datetime,hashlib,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent; RSI=R.parents[2]; now=datetime.datetime.now(datetime.timezone.utc).isoformat()
# Select only protocol lifecycle metadata; never export reasoning or tool payloads.
protocol=[]
for name in ('rpc_in.jsonl','rpc_out.jsonl'):
 p=RSI/'ikea/campaign/apple-0002/app-server'/name
 counts={};events=[]
 for line in p.open():
  try:e=json.loads(line)
  except ValueError:continue
  method=e.get('method');params=e.get('params',{});counts[str(method)]=counts.get(str(method),0)+1
  if method and ('turn/' in method or method=='error'):
   turn=params.get('turn',{})
   events.append({'method':method,'rpc_id':e.get('id'),'thread_id':params.get('threadId'),
      'turn_id':params.get('turnId',turn.get('id')),'status':turn.get('status')})
 protocol.append({'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'method_counts':counts,'turn_events':events})
(R/'pause-evidence/ikea-protocol-lifecycle.json').write_text(json.dumps(protocol,indent=2)+'\n')
ikea=json.loads((RSI/'ikea/campaign/apple-0002/result.json').read_text());ground=json.loads((RSI/'api-ground-to-table/actor-adapter/campaign/episode-0005/result.json').read_text())
for branch,path in [('ikea','ikea/campaign/apple-0002/result.json'),('ground','api-ground-to-table/actor-adapter/campaign/episode-0005/result.json')]:
 shutil.copyfile(RSI/path,R/f'pause-evidence/{branch}-original-result.json')
p=RSI/'api-ground-to-table/actor-adapter/campaign/episode-0005/video/episode.mp4'
probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,nb_frames','-of','json',str(p)],capture_output=True,text=True)
(R/'pause-evidence/ground-video-ffprobe.json').write_text(probe.stdout)
assert probe.returncode==0
pause={'at':now,'requested':True,'reason':'user_requested_pause','actual_actor_alive':False,'automatic_resume_allowed':False,
 'verification':'artifacts/architecture-review-20260916/six-task-focus/pause-status.json'}
for rel in ('ikea/state.json','ikea/actor-progress.json','ikea/web-progress.json'):
 p=RSI/rel; raw=p.read_bytes();dest=R/'pause-evidence'/('before-additive-pause__'+rel.replace('/','__'));dest.write_bytes(raw)
 value=json.loads(raw);value['user_pause']=pause
 # Preserve all pre-existing fields and atomically append the pause overlay.
 assert p.read_bytes()==raw,'Concurrent write: do not replace'
 tmp=p.with_suffix(p.suffix+'.user-pause-tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
status={'verified_at':now,'classification':'user_requested_pause','all_requested_branches_paused':True,
 'no_automatic_resume':True,'new_physics_or_model_calls':False,
 'ikea':{'episode':'apple-0002','actor_alive':False,'actor_app_server_alive':False,'continuation_owner_alive':False,
  'continuation_watcher_alive':False,'zero_model_heartbeat_alive':True,'actions':ikea['actions'],'sim_s':ikea['sim_s'],
  'native_outcome':ikea['outcome'],'raw_terminal_kind_preserved':ikea['terminal_kind'],'raw_error_preserved':ikea['error'],
  'administrative_stop_reason':'user_requested_pause','complete_model_turns':ikea['complete_model_turns'],
  'final_inflight_turn_complete':False,'skill_updated':ikea['skill_updated'],'remote_final_result':'unknown; no replay',
  'video_sealed':True,'video_probe':'pause-evidence/ikea-video-ffprobe.json','count_as_physical_failure':False,'count_as_success':False,
  'pause_marker_retained':True},
 'ground':{'episode':'episode-0005','actor_alive':False,'owner_alive':False,'watcher_pid':456959,'watcher_start_ticks':397394,
  'watcher_state':'blocked_zero_model_sleep_no_children','last_episode_termination':'HTTP429; preserved',
  'unknown_requests_preserved':['api-ground-002-call-55','api-ground-004-call-43','api-ground-005-call-10'],
  'video_sealed':True,'video_probe':'pause-evidence/ground-video-ffprobe.json','pause_marker_retained':True},
 'process_evidence':['pause-evidence/process-before.json','pause-evidence/process-after.json','pause-evidence/cancellation.json'],
 'sigkill_used':False,'shared_services_or_simple_touched':False,'original_results_or_trajectories_rewritten':False}
(R/'pause-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=R/'progress.json';v=json.loads(p.read_text());v.update(updated_utc=now,stage='pause_verified_preparing_six_task_candidates',ikea='paused_verified',ground='paused_verified',pause_status='pause-status.json');p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'ikea_actions':ikea['actions'],'ikea_turns_complete':ikea['complete_model_turns'],'video_sealed':True,'both_paused_verified':True}))
