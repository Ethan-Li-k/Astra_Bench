from pathlib import Path
import hashlib
import json
import subprocess
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
msg=(OUT/'handoff-launch.txt').read_bytes()
for name,thread in [('ui','01a0a980-7943-7963-9f36-b9c43c90c2da'),('framework','01a0a94d-6143-74c0-80cd-03d0b61acaf0')]:
    path=OUT/f'launch-queue-{name}.json'
    with path.open('x') as f:json.dump({'status':'attempt_started','at_unix':time.time()},f)
    r=subprocess.run([str(ROOT/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_reasoning_effort="xhigh"','--thread',thread,'--message',msg.decode()],capture_output=True)
    ok=r.returncode==0 and b'Queued' in r.stdout and b'usageLimitExceeded' not in r.stdout+r.stderr
    path.write_text(json.dumps({'thread':thread,'queued':ok,'acknowledged':False,'message_sha256':hashlib.sha256(msg).hexdigest(),'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'returncode':r.returncode},indent=2)+'\n')
    print(name,ok)
    if not ok:raise SystemExit('Queue stopped without retry')
