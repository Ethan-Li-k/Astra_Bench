"""Bind the already running auxiliary owner from verified host process IDs."""
import json
from pathlib import Path
import time
import watch
OUT=Path(__file__).resolve().parent
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='102fa58c-22af-4d56-bc78-f297d64f2a51'
expected=[dict(pid=335549,start_ticks=293878),dict(pid=335536,start_ticks=293874),dict(pid=335534,start_ticks=293874)]
assert all(watch.process_alive(p) for p in expected),'Original auxiliary owner identity changed'
log=OUT.parent/'continuation-003.jsonl'
events=watch.event_status(log)
assert events['thread']==watch.THREAD and not events['complete'] and not events['failure']
v=dict(thread=watch.THREAD,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    processes=expected,log=str(log),started_ns=1789552625000000000,
    binding_created_ns=time.time_ns(),source='Verified host ancestry of this running owner, never a new thread')
with (OUT/'active-owner.json').open('x') as f:f.write(json.dumps(v,indent=2)+'\n')
print(json.dumps(v))
