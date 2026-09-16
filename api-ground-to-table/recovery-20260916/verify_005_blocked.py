"""Read-only host/ledger/video verification, own-domain evidence writes only."""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/home/galbot/lizekai/RSI');REC=Path(__file__).resolve().parent;OUT=REC/'episode005-review'
sys.path.insert(0,str(REC/'supervision'));import watch
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def create(p,d):
    with p.open('x') as f:f.write(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
changed=[]
for manifest in (REC/'manifest.json',REC/'episode004-review/original-episode-manifest.json',OUT/'original-episode-manifest.json'):
    for row in json.loads(manifest.read_text()):
        if row['path'] in ('api-ground-to-table/status.json','api-ground-to-table/actor-adapter/auxiliary-progress.json') or row.get('exists') is False:continue
        p=ROOT/row['path']
        if not p.is_file() or ref(p)['sha256']!=row['sha256']:changed.append(row['path'])
assert not changed,changed
old=json.loads((OUT/'ledger-snapshot.json').read_text())['requests']
current=json.loads((ROOT/'artifacts/R020/shared-budget-ledger.json').read_text())['requests']
old_changed=[k for k,v in old.items() if k.startswith('api-ground-') and current.get(k)!=v]
assert not old_changed,old_changed
unknown=['api-ground-002-call-55','api-ground-004-call-43','api-ground-005-call-10']
for key in unknown:assert current[key]['state']=='inflight' and current[key]['reserved_fen']==1217
assert (ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002/api_calls/55/receipt.json').stat().st_size==0
assert (ROOT/'artifacts/R021/api-ground-002/api-ground-002-call-55-plan.json').stat().st_size==0
origin=json.loads((REC/'supervision/active-owner.json').read_text())
state=json.loads((REC/'supervision/owner-state.json').read_text())
ws=json.loads((REC/'supervision/watch-status.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert state['status']=='blocked' and state['blocker']=='gateway_http_429' and state['episode']=='episode-0005'
assert state['owner_log']==origin['log'] and state['written_ns']>=origin['started_ns']
assert origin['thread']==watch.THREAD and origin['boot_id']==boot
wid=watch.identity(ws['watcher_pid']);assert watch.process_alive(wid)
command=Path(f"/proc/{wid['pid']}/cmdline").read_bytes().split(b'\0')
assert b'watch.py' in command
assert Path(f"/proc/{wid['pid']}/cwd").resolve()==REC/'supervision'
with (REC/'supervision/owner.lock').open('a') as lock:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locked=False
    except BlockingIOError:locked=True
assert locked and not watch.actor_is_alive(state,boot)
owner_alive=any(watch.process_alive(p) for p in origin['processes']);assert owner_alive
tmux=subprocess.check_output(['tmux','list-sessions','-F','#{session_name}'],text=True).splitlines()
assert 'rsi-ground-continuation-0916' in tmux and 'rsi-api-ground-005-0916' not in tmux
public=json.loads((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_text())
assert public['state']=='ended' and public['actions']==4 and public['api_calls_completed']==9
assert public['last_physical_update_at_unix']==1789557019.357358
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8765/api/dashboard') as response:
    dashboard=json.loads(response.read())
create(OUT/'dashboard.json',dashboard)
req=urllib.request.Request('http://127.0.0.1:8765/videos/api-ground-episode-0005.mp4',headers={'Range':'bytes=0-1023'})
with opener.open(req) as response:
    status=response.status;headers=str(response.headers);data=response.read()
assert status==206 and len(data)==1024
with (OUT/'video-range-headers.txt').open('x') as f:f.write('HTTP status '+str(status)+'\n'+headers)
with (OUT/'video-range-1024.bin').open('xb') as f:f.write(data)
create(OUT/'final-verification.json',dict(at_unix=time.time(),owner=watch.THREAD,owner_alive=owner_alive,
    watcher_identity=wid,watcher_alive=True,owner_lock_held=True,actor_alive=False,origin=origin,owner_state=state,
    watcher_status_at_snapshot=ws,next_boundary='Current engineering turn natural exit, then existing watcher blocks automatic resume; no actor or next batch.',
    current_blocker='gateway_http_429',unknown_requests_retained=unknown,original002_004_005_files_changed=changed,
    original_ground_ledger_rows_changed=old_changed,public_progress=public,
    dashboard=ref(OUT/'dashboard.json'),video_range_status=status,video_range_bytes=len(data),
    no_model_or_gateway_requests=True,no_quota_price_queries=True))
print(json.dumps(dict(watcher_alive=True,watcher_pid=wid['pid'],owner_lock_held=True,actor_alive=False,
    unknown_requests_retained=unknown,old_changes=0,video_range=status,blocker='gateway_http_429')))
