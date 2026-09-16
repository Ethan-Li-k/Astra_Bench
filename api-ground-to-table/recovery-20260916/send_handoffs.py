"""Exactly one queue to each already-existing auxiliary thread. No resume."""
from pathlib import Path
import subprocess
import hashlib
import json
import time
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=ROOT/'api-ground-to-table/recovery-20260916'
for name,thread in [('ui','01a0a980-7943-7963-9f36-b9c43c90c2da'),('framework','01a0a94d-6143-74c0-80cd-03d0b61acaf0')]:
    receipt=OUT/('queue-'+name+'.json')
    if receipt.exists():
        raise SystemExit('Attempt already recorded; no duplicate queue')
    msg=OUT/('handoff-'+name+'.txt')
    raw=msg.read_bytes()
    record=dict(recipient=thread,message_sha256=hashlib.sha256(raw).hexdigest(),attempted_at_unix=time.time(),status='dispatch_started',acknowledged=False)
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    r=subprocess.run([str(ROOT/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_reasoning_effort="xhigh"','--thread',thread,'--message',raw.decode()],capture_output=True)
    (OUT/('queue-'+name+'.txt')).write_bytes(r.stdout+r.stderr)
    ok=r.returncode==0 and b'Queued' in r.stdout and b'usageLimitExceeded' not in r.stdout+r.stderr
    record.update(returncode=r.returncode,status='queued' if ok else 'not_confirmed',receipt_sha256=hashlib.sha256(r.stdout+r.stderr).hexdigest())
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if not ok: raise SystemExit('Queue blocked; no automatic retry')
