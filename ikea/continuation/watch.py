#!/usr/bin/env python3
"""Resume the existing secondary-account supervisor only after natural exit."""
import fcntl
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT / 'ikea/continuation'
THREAD = '01a0a96b-06cc-7150-8c73-7b0897936b52'
SESSION = 'rsi-ikea-engineer-0916'
FIRST_LOG = ROOT / 'ikea/recovery-20260916/engineer.jsonl'


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
    return state.get('state') if state.get('state') in ('continue', 'blocked', 'complete') else 'blocked_invalid_state'


def record(status, **extra):
    data = {'status': status, 'thread': THREAD, 'time_unix': time.time(), **extra}
    tmp = OUT / 'watch-status.tmp'
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(OUT / 'watch-status.json')
    print(json.dumps(data, ensure_ascii=False), flush=True)


def main():
    with (OUT / 'watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record('waiting_original_supervisor', model_calls=0)
        while True:
            if (OUT / 'PAUSE').exists():
                record('paused_before_resume')
                return
            r = subprocess.run(['tmux', 'has-session', '-t', SESSION], capture_output=True, text=True)
            if r.returncode:
                if 'Operation not permitted' in r.stderr or 'Permission denied' in r.stderr:
                    record('blocked_tmux_access')
                    return
                break
            time.sleep(15)
        previous, first = FIRST_LOG, True
        while not (OUT / 'PAUSE').exists():
            completed, failure = event_status(previous)
            state_path = ROOT / 'ikea/state.json'
            state = json.loads(state_path.read_text()) if state_path.exists() else None
            action = disposition(completed, failure, state, first)
            if action != 'continue':
                record(action, supervisor_state=state, previous_log=str(previous))
                return
            first = False
            stamp = str(time.time_ns())
            previous = OUT / f'resume-{stamp}.jsonl'
            prompt = (OUT / 'PROMPT.md').read_text()
            cmd = [str(ROOT/'codex-account-2/run.sh'), 'exec', '--approve-for-me',
                   '-C', str(ROOT/'ikea'), '--add-dir', str(ROOT),
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
