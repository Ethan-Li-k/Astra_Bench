"""Record launch-shell identity before it starts the unique locked actor."""
import json
import os
from pathlib import Path
import time
import watch
OUT=Path(__file__).resolve().parent
v=dict(episode='episode-0004',run_id='api-ground-004',owner=watch.THREAD,
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    processes=[watch.identity(os.getppid())],at_unix=time.time(),
    binding_kind='launch_shell_waits_for_actor_pipeline',
    result='api-ground-to-table/actor-adapter/campaign/episode-0004/result.json',
    exit_code='api-ground-to-table/recovery-20260916/run-004.exit-code')
with (OUT/'actor-004.json').open('x') as f:f.write(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
