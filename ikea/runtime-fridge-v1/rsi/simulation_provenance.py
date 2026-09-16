"""Host-only identity of a newly constructed simulation; never actor input."""
import datetime
import hashlib
import os
from pathlib import Path
import uuid


def reset_provenance(backend, seed):
    # Linux /proc stat field 22. Process names may contain spaces/parentheses.
    fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
    return {'method':'fresh_environment_reset','reset_id':str(uuid.uuid4()),
            'seed':seed,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'launch':{'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                      'pid':os.getpid(),'start_ticks':int(fields[19])},
            'post_settle_sim_s':float(backend.data.time),
            'post_settle_qpos_qvel_sha256':hashlib.sha256(
                backend.data.qpos.tobytes()+backend.data.qvel.tobytes()).hexdigest(),
            'note':'Reset invocation and process identity; not a success receipt or proof of task completion.'}
