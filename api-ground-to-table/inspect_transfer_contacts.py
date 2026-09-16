"""Scratch FK/contact geometry only: never a new rollout or actor input."""
import json
from pathlib import Path
import sys

ROOT = Path('/home/galbot/lizekai/RSI/api-ground-to-table/transfers/original-table-locomotion-001')
sys.path.insert(0, str(ROOT/'runtime'))
import mujoco
from rsi.live import tabletop_model

model = tabletop_model(table_only_offset_x=0.)
data = mujoco.MjData(model)
table = {i for i in range(model.ngeom) if 'diagnostic_table' in (model.geom(i).name or '')}
contacts = {}
samples = 0
for line in (ROOT/'video/robot_trace.jsonl').read_text().splitlines():
    record = json.loads(line)
    state = record['host_render_state']
    data.qpos[:] = state['qpos']
    data.qvel[:] = state['qvel']
    mujoco.mj_forward(model, data)
    samples += 1
    for contact in data.contact:
        pair = (int(contact.geom1), int(contact.geom2))
        if not set(pair) & table:
            continue
        name = '|'.join(model.geom(i).name or str(i) for i in pair)
        stats = contacts.setdefault(name, {'samples': 0, 'first_sim_s': record['sim_s'],
                                            'last_sim_s': record['sim_s'], 'min_distance_m': 0.})
        stats['samples'] += 1
        stats['last_sim_s'] = record['sim_s']
        stats['min_distance_m'] = min(stats['min_distance_m'], float(contact.dist))
result = {'kind': 'host_only_scratch_geometric_contact_review', 'new_physics': False,
          'actor_input_allowed': False, 'source_samples': samples,
          'contacts': contacts, 'interpretation': 'Geometry contact candidates, not measured forces or proven causal explanation.'}
(ROOT/'host_audit/geometric_table_contacts.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
