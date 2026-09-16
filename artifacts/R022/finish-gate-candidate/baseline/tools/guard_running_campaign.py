"""Temporary quota circuit breaker for the already-loaded R018 controller."""
import argparse
import json
import os
from pathlib import Path
import signal
import time

parser = argparse.ArgumentParser()
parser.add_argument('--pid', type=int, required=True)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--first', type=int, required=True)
args = parser.parse_args()
while Path(f'/proc/{args.pid}').exists():
    for episode in sorted(args.root.glob('episode-*'), reverse=True):
        if int(episode.name.split('-')[1]) < args.first:
            break
        snapshot, visible = episode/'SKILL.md', episode/'agent/SKILL.md'
        if snapshot.exists() and visible.parent.exists() and not visible.exists():
            visible.write_bytes(snapshot.read_bytes())
            print(json.dumps({'event': 'skill_snapshot_materialized',
                              'episode_id': episode.name}), flush=True)
        result_path = episode/'result.json'
        if not result_path.exists():
            continue
        try:
            result = json.loads(result_path.read_text())
        except json.JSONDecodeError:
            continue
        if 'usageLimitExceeded' not in str(result.get('error')):
            break
        # The old controller writes this only after closing the app-server,
        # then sleeps 30 s. Never kill during a live turn or on stale evidence.
        if time.time()-result_path.stat().st_mtime > 10:
            break
        children = Path(f'/proc/{args.pid}/task/{args.pid}/children').read_text().strip()
        command = Path(f'/proc/{args.pid}/cmdline').read_bytes()
        if not children and b'tools/learn_grasp_skill.py' in command:
            receipt = {'event': 'quota_circuit_breaker', 'pid': args.pid,
                       'episode_id': episode.name, 'result': str(result_path),
                       'no_live_child': True}
            (args.root/'quota_guard_stop.json').write_text(json.dumps(receipt, indent=2))
            os.kill(args.pid, signal.SIGTERM)
            print(json.dumps(receipt), flush=True)
            raise SystemExit(0)
        break
    time.sleep(1)
print('Controller exited; quota guard finished.', flush=True)
