"""Two authorized auxiliary queue deliveries, sequential, no inference/resume/retry."""
import hashlib
import json
from pathlib import Path
import subprocess
import datetime

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT / 'api-ground-to-table/progress-ui-verification'
records = []
for name, thread in [('api', '01a0a948-10bb-7d03-8f1d-b1eeda7cb93c'),
                     ('review', '01a0a94d-6143-74c0-80cd-03d0b61acaf0')]:
    message = OUT / ('handoff-' + name + '.txt')
    receipt = OUT / ('queue-' + name + '-receipt.txt')
    if receipt.exists():
        raise SystemExit('Existing receipt; do not send duplicate queue')
    raw = message.read_bytes()
    cmd = [str(ROOT / 'codex-account-2/run.sh'), 'queue', '-m', 'gpt-6-astra',
           '-c', 'model_reasoning_effort="xhigh"', '--thread', thread,
           '--message', raw.decode()]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    receipt.write_bytes(result.stdout)
    print(name, result.stdout.decode(errors='replace'), flush=True)
    ok = result.returncode == 0 and b'usageLimitExceeded' not in result.stdout and b'Queued' in result.stdout
    records.append(dict(recipient=thread, message_file=str(message.relative_to(ROOT)),
        message_offset=0, message_bytes=len(raw), message_sha256=hashlib.sha256(raw).hexdigest(),
        receipt_file=str(receipt.relative_to(ROOT)), receipt_sha256=hashlib.sha256(result.stdout).hexdigest(),
        returncode=result.returncode, status='queued' if ok else 'not_confirmed',
        at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        acknowledged=False, integrated=False, physical_validation=False))
    (OUT / 'queue-status.json').write_text(json.dumps(records, indent=2)+'\n')
    if not ok:
        raise SystemExit('Queue not confirmed or limit reached; stop without retry or second delivery')
