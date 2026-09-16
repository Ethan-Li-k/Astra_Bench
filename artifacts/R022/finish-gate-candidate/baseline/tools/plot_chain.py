"""Static scientific plots from saved controller traces, no simulation."""
from pathlib import Path
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path('artifacts/R006')
parser=argparse.ArgumentParser()
parser.add_argument('--arm',choices=('left','right'),default='left')
arm=parser.parse_args().arm
suffix='' if arm=='left' else '_right'
fig,axes=plt.subplots(5,2,figsize=(13,13),sharex=True,constrained_layout=True)
for col,run in enumerate(('raw-chain-02','servo-chain-01')):
    d=np.load(root/run/'chain.npz');z=np.load(root/run/'fsq_verified.npz')
    t=d['sim_s'];keep=(t>=10)&(t<=12);j=d['joint_names'].tolist().index(f'{arm}_elbow_joint')
    wrist=d['body_names'].tolist().index(f'{arm}_wrist_yaw_link')
    axes[0,col].set_title('Original tracker' if col==0 else 'Reference servo candidate (rejected)')
    delta=d['tracker_pos'][:,0,wrist]-d['nominal_pos'][:,0,wrist]
    for axis,label in enumerate(('X','Y','Z')):
        axes[0,col].plot(t[keep],delta[keep,axis]*1000,label=label)
    axes[0,col].set_ylabel('Tracker ref - requested\nworld ref (mm)')
    axes[0,col].set_ylim(-55,15)
    features=d['policy_task'][:,0,168+6*wrist:174+6*wrist]
    feature=3
    x=features[:,feature]
    axes[1,col].plot(t[keep],x[keep]-x[keep].mean(),color='#7053a0',label=f'6D component {feature}')
    axes[1,col].set_ylabel('Wrist orientation-error\nfeature (mean removed)')
    flips=np.count_nonzero(np.diff(z['codes'],axis=0),axis=1)
    zt=t[z['indices'][1:]];zk=(zt>=10)&(zt<=12)
    axes[2,col].step(zt[zk],flips[zk],where='post',color='#b47b1a',label='Verified reconstruction')
    axes[2,col].set_ylabel('FSQ dimensions changed\nper 20 ms')
    axes[2,col].set_ylim(0,14)
    for values,label,color in [(d['q_target'],'Model target','#d07924'),(d['q_after'],'Actual joint','#146aa1')]:
        x=np.rad2deg(values[:,j]);mean=x[keep].mean()
        axes[3,col].plot(t[keep],x[keep]-mean,label=f'{label}, mean {mean:.1f} deg',color=color)
    axes[3,col].set_ylabel(f'{arm.title()} elbow angle\n(deg, own mean removed)')
    axes[3,col].set_ylim(-3,3)
    st=d['substep_s'];sk=(st>=10)&(st<=12)
    axes[4,col].plot(st[sk],d['torque_sent'][sk,j],color='#246f52',label='Actual PD command')
    axes[4,col].set_ylabel(f'{arm.title()} elbow torque (Nm)')
    axes[4,col].set_xlabel('Simulation time (s)')
    for ax in axes[:,col]:
        ax.legend(loc='upper right',fontsize=7);ax.grid(alpha=.2);ax.set_xlim(10,12)
fig.suptitle('Synchronized signal chain: constant user goals do not imply constant model inputs',fontsize=14)
fig.savefig(root/f'signal_chain{suffix}.png',dpi=150)
plt.close(fig)

fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,constrained_layout=True)
for run,label,color in [('raw-chain-02','No intervention','#777777'),('freeze-wrists-01','Freeze wrist task fields only','#a84636')]:
    d=np.load(root/run/'chain.npz');t=d['sim_s'];keep=(t>=8.5)&(t<=14.3)
    j=d['joint_names'].tolist().index(f'{arm}_elbow_joint')
    axes[0].plot(t[keep],np.rad2deg(d['q_target'][keep,j]),label=label,color=color,alpha=.8)
    axes[1].plot(t[keep],np.rad2deg(d['q_after'][keep,j]),label=label,color=color,alpha=.8)
for ax in axes:
    ax.axvspan(10,12,color='#ddc091',alpha=.25,label='Diagnostic freeze interval')
    ax.grid(alpha=.2);ax.legend(fontsize=8)
axes[0].set_ylabel('Model elbow target (deg)');axes[1].set_ylabel('Actual elbow angle (deg)')
axes[1].set_xlabel('Simulation time (s)')
fig.suptitle('Freezing feedback is not a repair: target jumps shrink while actual pose drifts')
fig.savefig(root/f'freeze_feedback{suffix}.png',dpi=150)
plt.close(fig)
