"""One-shot infrastructure recovery, never a campaign/model resume watcher.

Stop ONLY the broken episode's Python owner at a complete model-turn boundary.
If a new turn raced ahead, immediately release the owner and await its completion.
The app-server is never signalled with an unmatched turn/start.
"""
import ctypes
import json
import os
from pathlib import Path
import select
import signal
import time

episode=Path(__file__).resolve().parent
thread='01a0a8f3-5c94-7bf3-85af-451b773a6063'
def args(pid):
    try:return Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
    except (FileNotFoundError,ProcessLookupError,PermissionError):return []
owners=[int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit()
        and 'tools/learn_simple_task.py' in args(p.name)
        and 'simple/G1WholebodyOpenFaucetTeleop-v0' in args(p.name)]
assert len(owners)==1,owners
owner=owners[0]
children=Path(f'/proc/{owner}/task/{owner}/children').read_text().split()
servers=[int(p) for p in children if 'app-server' in args(p)]
assert len(servers)==1,servers
server=servers[0]
assert os.getpgid(server)==server
def messages(name):
    result=[]
    for line in (episode/'app_server'/name).read_text().splitlines():
        try:result.append(json.loads(line))
        except json.JSONDecodeError:pass
    return result
libc=ctypes.CDLL(None,use_errno=True)
fd=libc.inotify_init1(os.O_NONBLOCK)
assert fd>=0
assert libc.inotify_add_watch(fd,os.fsencode(episode/'app_server/rpc_out.jsonl'),2)>=0
seen={m['params']['turn']['id'] for m in messages('rpc_out.jsonl')
      if m.get('method')=='turn/completed'}
print(json.dumps({'event':'await_complete_boundary','owner_pid':owner,'server_pid':server}),flush=True)
try:
    while True:
        ready,_,_=select.select([fd],[],[],60)
        if not ready:continue
        try:os.read(fd,65536)
        except BlockingIOError:pass
        # Pausing the owner does not stop inference in its independent app-server.
        # Pause immediately on output notification; parsing before this step
        # would always lose the very short completed-turn/next-start boundary.
        os.kill(owner,signal.SIGSTOP)
        try:
            incoming=messages('rpc_in.jsonl');out=messages('rpc_out.jsonl')
            starts=[m for m in incoming if m.get('method')=='turn/start'
                    and m['params'].get('threadId')==thread]
            replies={m['id']:m.get('result') for m in out if 'id' in m and 'method' not in m}
            complete={m['params']['turn']['id']:m['params']['turn'].get('status')
                      for m in out if m.get('method')=='turn/completed'
                      and m['params'].get('threadId')==thread}
            ids=[(replies.get(m['id']) or {}).get('turn',{}).get('id') for m in starts]
            if not ids or any(t is None or complete.get(t)!='completed' for t in ids):
                if set(complete)-seen:
                    print(json.dumps({'event':'new_turn_raced_ahead_waiting_without_interruption',
                                      'completed_turns':len(complete)}),flush=True)
                seen.update(complete)
                continue
            proof={'status':'safe_complete_turn_boundary','owner_pid':owner,'server_pid':server,
                   'thread_id':thread,'completed_turn_ids':ids,'unmatched_turn_start':False,
                   'reason':'Known admitted-but-unexecuted duration error; stop automatic empty retries.',
                   'skill_revision':'Pending separate complete evidence review; not fabricated.',
                   'physical_action_count':1,'physical_task_success':False}
            (episode/'infrastructure_boundary_stop.json').write_text(json.dumps(proof,indent=2)+'\n')
            os.killpg(server,signal.SIGTERM)
            # Ensure _send cannot launch another model turn when the owner resumes.
            while Path(f'/proc/{server}/stat').exists():
                state=Path(f'/proc/{server}/stat').read_text().split(') ',1)[1].split()[0]
                if state=='Z':break
                time.sleep(.02)
            print(json.dumps({'event':'idle_app_server_stopped','complete_turns':len(ids)}),flush=True)
            break
        finally:
            os.kill(owner,signal.SIGCONT)
finally:
    os.close(fd)
