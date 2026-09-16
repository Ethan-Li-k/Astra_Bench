"""Zero-model heartbeat; never starts, resumes, stops or retries an actor."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
lock = (ROOT / 'progress-watch.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
while True:
    state = json.loads((ROOT / 'state.json').read_text())
    heartbeat = {
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'state': state['state'], 'phase': state['phase'],
        'decision_updated_at': state['updated_at'],
        'role_thread': state['thread_id'], 'watcher_pid': os.getpid(),
        'model_calls': 0, 'actor_progress': None,
        'note': 'Heartbeat is liveness monitoring, not evidence of physical progress.'}
    actor = ROOT / 'actor-progress.json'
    if actor.exists():
        heartbeat['actor_progress'] = json.loads(actor.read_text())
    tmp = ROOT / 'heartbeat.next.json'
    tmp.write_text(json.dumps(heartbeat, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(ROOT / 'heartbeat.json')
    print(json.dumps(heartbeat, ensure_ascii=False), flush=True)
    if state['state'] in ('complete', 'blocked'):
        break
    time.sleep(30)
