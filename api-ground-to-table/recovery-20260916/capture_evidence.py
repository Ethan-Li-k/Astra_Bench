"""Read original evidence once; write only a separately named recovery snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT / 'api-ground-to-table/recovery-20260916'
SNAP = OUT / 'original-snapshot'
SNAP.mkdir(exist_ok=False)
paths = [ROOT/'api-ground-to-table/status.json', ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json']
for rel in ['api-ground-to-table/actor-adapter/campaign/episode-0002', 'artifacts/R021/api-ground-002']:
    paths.extend(p for p in (ROOT/rel).rglob('*') if p.is_file())
paths.extend([ROOT/'api-ground-to-table/actor-adapter/run-002.log', ROOT/'artifacts/R021/shared-budget-ledger.json'])
manifest = []
for p in sorted(set(paths)):
    if not p.exists():
        manifest.append({'path':str(p.relative_to(ROOT)), 'exists':False})
        continue
    raw = p.read_bytes()
    rel = p.relative_to(ROOT)
    dest = SNAP / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
    item = {'path':str(rel), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(), 'mtime_ns':p.stat().st_mtime_ns}
    if p.suffix in ('.json', '.jsonl', '.log'):
        item['nul_bytes'] = raw.count(b'\x00')
    if p.suffix == '.json':
        try:
            json.loads(raw)
            item['json_valid'] = True
        except (ValueError, UnicodeDecodeError):
            item['json_valid'] = False
    manifest.append(item)
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {'command':cmd, 'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
evidence = {'captured_at_unix':time.time(), 'owner_thread':os.environ.get('CODEX_THREAD_ID'),
    'account_home':os.environ.get('CODEX_HOME'), 'model':'gpt-6-astra', 'effort':'xhigh',
    'boot':run(['uptime','-s']), 'old_pids':run(['ps','-p','3537389,3431415','-o','pid=,comm=,lstart=']),
    'tmux':run(['tmux','list-sessions','-F','#{session_name}']),
    'video_probe':run(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height,avg_frame_rate','-of','json',str(ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002/video/episode.mp4')])}
(OUT/'infrastructure-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({'snapshot_files':len(manifest),'empty_files':[x['path'] for x in manifest if x.get('bytes')==0], 'infrastructure':evidence},indent=2))
