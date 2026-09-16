"""Saved single-axis response measurements; never used as a control inverse."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path('artifacts/R008')
fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
report = {'scope': 'Local +20mm nominal-reference steps from one initial pose; not global calibration or grasp evaluation',
          'windows_s': {'before': [8, 10], 'after': [18, 20]}, 'runs': {}}
for col, backend in enumerate(('onnx', 'continuous')):
    for row, axis in enumerate('xyz'):
        name = f'reference-{axis}-{backend}'
        d = np.load(root/name/'chain.npz'); t = d['sim_s']
        before, after = (t >= 8) & (t < 10), t >= 18
        w = d['body_names'].tolist().index('right_wrist_yaw_link')
        measured = d['body_after'][:, w]
        origin = measured[before].mean(0)
        requested = d['nominal_pos'][-1, 0, w] - d['nominal_pos'][0, 0, w]
        expected = np.eye(3)['xyz'.index(axis)]*.02
        np.testing.assert_allclose(requested, expected, atol=1e-7)
        result = json.loads((root/name/'summary.json').read_text())
        report['runs'][name] = dict(stop_reason=result['reason'], sim_s=result['sim_s'],
            reference_delta_mm=(requested*1000).tolist(),
            actual_delta_mm=((measured[after].mean(0)-origin)*1000).tolist(),
            post_wrist_std_mm=(measured[after].std(0)*1000).tolist(),
            post_goal_error_mm=float(np.linalg.norm(measured[after].mean(0)-d['nominal_pos'][-1,0,w])*1000))
        ax = axes[row, col]
        for i, label in enumerate('XYZ'):
            ax.plot(t, (measured[:,i]-origin[i])*1000, label=f'Actual {label}')
        ax.plot(t, (d['nominal_pos'][:,0,w,'xyz'.index(axis)]-d['nominal_pos'][0,0,w,'xyz'.index(axis)])*1000,
                color='black', linestyle='--', alpha=.5, label=f'Reference {axis.upper()}')
        ax.set_xlim(8,20); ax.set_ylim(-13,27); ax.grid(alpha=.2)
        ax.set_title(f'{backend}: +20mm {axis.upper()} reference'); ax.legend(fontsize=7)
        ax.set_ylabel('Wrist displacement (mm)')
for ax in axes[-1]: ax.set_xlabel('Simulation time (s)')
fig.suptitle('Single-axis reference changes: unequal motion response remains without FSQ rounding')
fig.savefig(root/'reference_steps.png', dpi=150)
(root/'reference_step_analysis.json').write_text(json.dumps(report,indent=2))
for name, row in report['runs'].items():
    print(name, 'actual mm:', np.round(row['actual_delta_mm'],3).tolist(), 'goal error mm:', round(row['post_goal_error_mm'],2))
