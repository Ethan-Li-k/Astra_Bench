#!/usr/bin/env python3
"""Single ground owner continuation, adapted from account2/continuation/watch.py.

No simulator control or API retries. Resume the same auxiliary engineering thread
only after its verified complete turn/process and bound actor have both ended.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path('/home/galbot/lizekai/RSI')
OUT=Path(__file__).resolve().parent
THREAD='01a0a982-cec5-71c0-b771-091c31df61f2'

def write(path,data):
    tmp=path.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    tmp.replace(path)

def process_alive(identity):
    try:
        tail=Path(f"/proc/{identity['pid']}/stat").read_text().rsplit(')',1)[1].split()
        return tail[0]!='Z' and int(tail[19])==identity['start_ticks']
    except FileNotFoundError:return False

def identity(pid):
    tail=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,start_ticks=int(tail[19]))

def event_status(path):
    started=False;complete=False;failure=None;thread=None
    for line in path.read_text().splitlines():
        try:e=json.loads(line)
        except ValueError:continue
        if e.get('type')=='thread.started':thread=e.get('thread_id')
        elif e.get('type')=='turn.started':started=True;complete=False;failure=None
        elif e.get('type') in ('error','turn.failed'):failure=e.get('type')
        elif e.get('type')=='turn.completed':complete=True
    return dict(complete=started and complete,failure=failure,thread=thread)

def decision(origin,state,event,owner_alive,actor_alive,used,boot):
    if origin.get('boot_id')!=boot or origin.get('thread')!=THREAD:return 'blocked_identity'
    if owner_alive:return 'waiting_owner_natural_exit'
    if event.get('thread')!=THREAD or not event.get('complete') or event.get('failure'):
        return 'blocked_protocol_error_or_incomplete_turn'
    if not state or state.get('owner_log')!=origin['log'] or state.get('written_ns',0)<origin['started_ns']:
        return 'blocked_missing_fresh_disposition'
    if state.get('status')!='continue':return 'blocked_owner_disposition'
    if not state.get('episode') or state['episode'] in used:return 'blocked_repeated_boundary'
    if actor_alive:return 'waiting_actor_natural_exit'
    return 'resume'

def record(status,**extra):
    v=dict(status=status,owner=THREAD,watcher_pid=os.getpid(),updated_at_unix=time.time(),
           heartbeat_is_not_physical_progress=True,**extra)
    write(OUT/'watch-status.json',v);print(json.dumps(v,ensure_ascii=False),flush=True)

def blocked(reason,**extra):
    record(reason,**extra)
    # Report the supervision boundary without changing physical counters/state.
    for path in (ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',
                 OUT.parent/'progress.json',ROOT/'api-ground-to-table/status.json'):
        if path.exists():
            v=json.loads(path.read_text())
            v.update(supervisor_blocker=reason,supervisor_alive=True,
                     current_problem='持续监督暂停自动接续：'+reason,
                     next_step='需核对监督日志及原回合实际状态后，由当前辅助owner处理；未知请求不重发。',
                     updated_at_unix=time.time())
            write(path,v)
    with (OUT.parent/'RECOVERY.md').open('a') as f:
        f.write(f'\n监督阻塞 {time.time()}: {reason}；未自动重试，请核对supervision/watch-status.json。原物理计数保持。\n')
    # Remain an observable supervisor, but never retry a failed/uncertain turn.
    while True:time.sleep(15)

def actor_is_alive(state,boot):
    path=ROOT/state['actor_binding']
    if not path.is_file():raise ValueError('Actor binding absent; cannot assume no actor')
    a=json.loads(path.read_text())
    if a.get('boot_id')!=boot or a.get('episode')!=state['episode']:
        raise ValueError('Actor identity mismatch')
    for proc in a['processes']:
        if process_alive(proc):return True
    return False

def main():
    with (OUT/'owner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        origin=json.loads((OUT/'active-owner.json').read_text())
        used=set();last=None
        while True:
            if (OUT/'PAUSE').exists():blocked('paused_before_resume')
            state_path=OUT/'owner-state.json'
            state=json.loads(state_path.read_text()) if state_path.exists() else None
            alive=any(process_alive(p) for p in origin['processes'])
            event=event_status(Path(origin['log']))
            try:actor_alive=actor_is_alive(state,boot) if state and not alive else False
            except (KeyError,ValueError,OSError) as e:blocked('blocked_actor_identity',error=str(e))
            action=decision(origin,state,event,alive,actor_alive,used,boot)
            if action!=last:
                record(action,owner_log=origin['log'],episode=(state or {}).get('episode'));last=action
            if action.startswith('blocked'):blocked(action)
            if action!='resume':time.sleep(15);continue
            used.add(state['episode'])
            stamp=str(time.time_ns());log=OUT/f'resume-{stamp}.jsonl'
            started=time.time_ns()
            prompt=(OUT/'PROMPT.md').read_text()
            cmd=[str(ROOT/'codex-account-2/run.sh'),'exec','--approve-for-me',
                 '-C',str(ROOT),'--add-dir',str(ROOT),'--disable','multi_agent','--disable','memories',
                 '-c','model_provider="openai"','-c','model_reasoning_effort="xhigh"',
                 'resume','--json','--skip-git-repo-check','--model','gpt-6-astra',
                 '--output-last-message',str(OUT/f'resume-{stamp}-final.md'),THREAD,'-']
            record('resuming_existing_auxiliary_owner',log=str(log),boundary=state['episode'])
            with log.open('x') as f:
                p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,text=True)
                origin=dict(thread=THREAD,boot_id=boot,log=str(log),started_ns=started,
                            processes=[identity(p.pid)],parent_watcher_pid=os.getpid())
                write(OUT/'active-owner.json',origin)
                p.stdin.write(prompt);p.stdin.close()
                for line in p.stdout:
                    f.write(line);f.flush();print(line,end='',flush=True)
                rc=p.wait()  # No inference deadline, kill, retry, new account or thread.
            if rc:blocked('blocked_auxiliary_exit',returncode=rc,log=str(log))
            last=None

if __name__=='__main__':main()
