#!/usr/bin/env python3
"""Resume the existing secondary-account supervisor only after natural exit."""
import fcntl
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT / 'codex-account-2/continuation'
THREAD = '01a0a867-d7aa-71f2-8547-e264d6d09ede'
SESSION = 'rsi-account2-supervisor-0915'
FIRST_LOG = ROOT / 'artifacts/R019/account2-supervisor-0915.jsonl'


def supervisor_origin():
    path = OUT / 'active-supervisor.json'
    if not path.exists():
        return {'session': SESSION, 'previous_log': str(FIRST_LOG), 'started_ns': 0}
    origin = json.loads(path.read_text())
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if origin.get('thread') != THREAD or origin.get('boot_id') != boot:
        raise ValueError('Supervisor origin thread/boot does not match; explicit recovery required')
    log = Path(origin['previous_log']).resolve()
    if log.parent != OUT.resolve() or not log.is_file() or not origin.get('session'):
        raise ValueError('Invalid current supervisor session/log binding')
    return origin


def origin_process_alive(origin):
    pid = origin.get('pid', 0)
    if not pid:
        return False
    try:
        tail = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return tail[0] != 'Z' and int(tail[19]) == origin.get('start_ticks')
    except FileNotFoundError:
        return False


def event_status(path):
    """Only actual protocol error events count; quoted historical text does not."""
    completed = False
    failure = None
    with path.open() as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get('type')
            if kind == 'turn.started':
                completed, failure = False, None
            elif kind in ('error', 'turn.failed'):
                failure = event
            elif kind == 'turn.completed':
                completed = True
    return completed, failure


def disposition(completed, failure, state, first):
    if failure or not completed:
        return 'blocked_protocol_error_or_incomplete_turn'
    if state is None:
        return 'continue' if first else 'blocked_missing_supervisor_state'
    return state.get('status') if state.get('status') in ('continue', 'blocked', 'complete') else 'blocked_invalid_state'


def record(status, **extra):
    data = {'status': status, 'thread': THREAD, 'time_unix': time.time(), **extra}
    tmp = OUT / 'watch-status.tmp'
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(OUT / 'watch-status.json')
    print(json.dumps(data, ensure_ascii=False), flush=True)


def main():
    with (OUT / 'watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            origin = supervisor_origin()
        except (ValueError, KeyError, OSError) as exc:
            record('blocked_invalid_supervisor_origin', error=str(exc))
            return
        record('waiting_original_supervisor', model_calls=0, origin=origin)
        while True:
            if (OUT / 'PAUSE').exists():
                record('paused_before_resume')
                return
            r = subprocess.run(['tmux', 'has-session', '-t', origin['session']], capture_output=True, text=True)
            if r.returncode:
                if 'Operation not permitted' in r.stderr or 'Permission denied' in r.stderr:
                    record('blocked_tmux_access')
                    return
                if not origin_process_alive(origin):
                    break
            time.sleep(15)
        previous, first = Path(origin['previous_log']), True
        while not (OUT / 'PAUSE').exists():
            completed, failure = event_status(previous)
            state_path = OUT / 'supervisor-state.json'
            state = json.loads(state_path.read_text()) if state_path.exists() else None
            if first and origin.get('started_ns', 0) and (
                    not state_path.exists() or state_path.stat().st_mtime_ns < origin['started_ns']):
                record('blocked_missing_fresh_supervisor_state', previous_log=str(previous))
                return
            action = disposition(completed, failure, state, first)
            if action != 'continue':
                record(action, supervisor_state=state, previous_log=str(previous))
                return
            first = False
            stamp = str(time.time_ns())
            previous = OUT / f'resume-{stamp}.jsonl'
            prompt = (OUT / 'PROMPT.md').read_text()
            cmd = [str(ROOT/'codex-account-2/run.sh'), 'exec', '--approve-for-me',
                   '-C', str(ROOT/'codex-account-2/workspace'), '--add-dir', str(ROOT),
                   '--disable', 'multi_agent', '--disable', 'memories',
                   '-c', 'model_provider="openai"', '-c', 'model_reasoning_effort="xhigh"',
                   'resume', '--json', '--skip-git-repo-check', '--model', 'gpt-6-astra',
                   '--output-last-message', str(OUT/f'resume-{stamp}-final.md'), THREAD, '-']
            record('resuming_after_completed_turn', log=str(previous))
            started = time.time_ns()
            with previous.open('w') as log:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True)
                p.stdin.write(prompt)
                p.stdin.close()
                for line in p.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end='', flush=True)
                rc = p.wait()  # No wall-clock inference timeout or automatic cancellation.
            if rc:
                record('blocked_cli_exit', exit_code=rc, log=str(previous))
                return
            if not state_path.exists() or state_path.stat().st_mtime_ns < started:
                record('blocked_missing_fresh_supervisor_state', log=str(previous))
                return
        record('paused_before_resume')


if __name__ == '__main__':
    main()
