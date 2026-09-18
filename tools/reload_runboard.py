#!/usr/bin/env python3
"""Reload only the read-only dashboard collector; never signal an actor/server."""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'artifacts/api-first-20260916/update_live_page.py'
BOARD = TARGET.with_name('runboard.py')


def reload_collector():
    for source in (TARGET, BOARD):
        compile(source.read_text(), str(source), 'exec')
    found = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            if str(TARGET).encode() in (proc/'cmdline').read_bytes().split(b'\0'):
                found.append(proc)
        except OSError:
            continue
    if len(found) != 1:
        raise RuntimeError(f'Expected one dashboard collector; found {len(found)}. No process signaled.')
    proc = found[0]
    executable = os.readlink(proc/'exe')
    if str(TARGET).encode() not in (proc/'cmdline').read_bytes().split(b'\0'):
        raise RuntimeError('Collector identity changed. No process signaled.')
    os.kill(int(proc.name), signal.SIGTERM)
    for _ in range(50):
        if not proc.exists():
            break
        time.sleep(.1)
    if proc.exists():
        raise RuntimeError('Old collector did not exit; no second collector started.')
    started = time.time()
    session = f'rsi-board-{time.strftime("%m%d")}-{int(started)}'
    command = (shlex.join([executable, str(TARGET)]) + ' 2>&1 | tee -a '
               + shlex.quote(str(TARGET.with_name('live-page.log'))))
    subprocess.run(['tmux', 'new-session', '-d', '-s', session, '-c', str(ROOT), command], check=True)
    result = TARGET.parent/'web/runboard.json'
    for _ in range(100):
        if result.is_file() and result.stat().st_mtime >= started:
            data = json.loads(result.read_text())
            return dict(status='updated', session=session, updated_at=data['updated_at'],
                        actors_signaled=0, models_started=0, server_restarted=False)
        time.sleep(.1)
    raise RuntimeError('Collector started but no fresh dashboard snapshot appeared; inspect live-page.log.')


if __name__ == '__main__':
    print(json.dumps(reload_collector(), ensure_ascii=False))
