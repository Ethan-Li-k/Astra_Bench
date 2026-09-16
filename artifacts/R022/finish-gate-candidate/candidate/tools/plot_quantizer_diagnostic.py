"""Compare saved single-factor quantizer experiments; no robot control."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path('artifacts/R006')
fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
for col, side in enumerate(('left', 'right')):
    for run, label, color in [('torch-raw-01', 'Original quantized semantics', '#bb5939'),
                              ('continuous-diagnostic-01', 'Without rounding (diagnostic)', '#167f87')]:
        d = np.load(root/run/'chain.npz')
        t = d['sim_s']; keep = (t >= 10) & (t <= 12)
        j = d['joint_names'].tolist().index(f'{side}_elbow_joint')
        angle = np.rad2deg(d['q_after'][keep, j])
        axes[0, col].plot(t[keep], angle-angle.mean(), label=label, color=color)
    axes[0, col].set_title(f'{side.title()} elbow: stationary reference')
    axes[0, col].set_ylabel('Actual angle, own mean removed (deg)')
    axes[0, col].set_ylim(-.8, .8)
    axes[0, col].legend(fontsize=8)

d = np.load(root/'continuous-move-01/chain.npz')
t = d['sim_s']; keep = t >= 9
w = d['body_names'].tolist().index('right_wrist_yaw_link')
anchor = d['body_pos'][500, w]
for axis, label in enumerate(('X', 'Y', 'Z')):
    axes[1, 0].plot(t[keep], (d['body_after'][keep, w, axis]-anchor[axis])*1000, label=label)
goal = d['nominal_pos'][-1, 0, w]
err = np.linalg.norm(d['body_after'][:, w]-goal, axis=1)*1000
axes[1, 1].plot(t[keep], err[keep], color='#7053a0', label='3D error to final goal')
axes[1, 1].axhline(10, color='gray', linestyle='--', label='Arrival threshold')
axes[1, 0].set_title('Continuous diagnostic: +20 mm world-X command')
axes[1, 0].set_ylabel('Right wrist displacement (mm)')
axes[1, 1].set_title('Motion responds, but arrival times out')
axes[1, 1].set_ylabel('Position error (mm)')
for ax in axes[1]:
    ax.axvline(10, color='gray', linestyle=':', label='Command start')
    ax.legend(fontsize=8)
for ax in axes.flat:
    ax.grid(alpha=.2); ax.set_xlabel('Simulation time (s)')
fig.suptitle('Removing FSQ rounding isolates jitter; it does not solve tracking bias')
fig.savefig(root/'quantizer_diagnostic.png', dpi=150)
