"""Original tabletop location, floor target; independent API process only."""
from pathlib import Path
import hashlib
import json
import sys

FROZEN = Path('/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table/provenance/episodes/episode-0007')


def create_backend():
    manifest = json.loads((FROZEN/'setting_manifest.json').read_text())
    original_root = FROZEN.parents[2]
    for absolute, expected in manifest['episode_runtime_hashes'].items():
        path = FROZEN/Path(absolute).relative_to(original_root)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen runtime changed: '+str(path))
    sys.path.insert(0, str(FROZEN))
    import ground_task
    if Path(ground_task.__file__).resolve() != FROZEN/'ground_task.py':
        raise RuntimeError('Must load the reviewed frozen ground runtime')
    factory = ground_task.tabletop_model
    # Restore table during construction, before any reset/physics/sealing.
    ground_task.tabletop_model = lambda **kwargs: factory(table_only_offset_x=0.)
    try:
        backend = ground_task.create_backend(continuous=True)
    finally:
        ground_task.tabletop_model = factory
    backend.reset_provenance.update(original_table_offset_m=0,
        source_runtime=str(FROZEN), human_feedback_used=True, human_demonstration_used=False)
    return backend
