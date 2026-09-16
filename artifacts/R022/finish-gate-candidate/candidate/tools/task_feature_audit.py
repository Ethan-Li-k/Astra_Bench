"""One-step task-feature substitutions on recorded inputs; no live control."""
import argparse
import json
from pathlib import Path
import numpy as np
import onnxruntime as ort


def main():
    p=argparse.ArgumentParser()
    p.add_argument('trace',type=Path)
    args=p.parse_args()
    d=np.load(args.trace/'chain.npz')
    output=args.trace/'feature_audit.json'
    if output.exists():raise FileExistsError(output)
    i=np.flatnonzero(d['sim_s']>=10)
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1
    model=ort.InferenceSession('/home/galbot/Downloads/model_38000.onnx',options,providers=['CPUExecutionProvider'])
    task=d['policy_task'][i]; fixed=np.repeat(task[:1],len(i),axis=0)
    groups={'absolute_position':np.arange(0,42),'position_error':np.arange(42,84),
            'absolute_orientation':np.arange(84,168),'orientation_error':np.arange(168,252)}
    for b in np.flatnonzero(d['mode'][0]):
        groups[str(d['body_names'][b])]=np.r_[np.arange(b*3,b*3+3),np.arange(42+b*3,45+b*3),
                                            np.arange(84+b*6,90+b*6),np.arange(168+b*6,174+b*6)]
    results={}
    for name,columns in groups.items():
        varied=fixed.copy();varied[:,:,columns]=task[:,:,columns]
        outputs=[]
        for start in range(0,len(i),32):
            x=varied[start:start+32];n=len(x)
            outputs.append(model.run(['actions'],{'policy_task':x,
                'policy':np.repeat(d['policy'][i[:1]],n,axis=0),
                'action':np.repeat(d['action_history_in'][i[:1]],n,axis=0),
                'mode':np.repeat(d['mode'],n,axis=0),'mode_mapping':np.repeat(d['mode_mapping'],n,axis=0)})[0])
        delta=np.diff(np.concatenate(outputs)*d['scale'],axis=0)
        masked=task[:,:,columns]*d['mode_mapping'][0,columns]
        results[name]={'target_step_rms_deg':np.rad2deg(np.sqrt(np.mean(delta**2,axis=0))).tolist(),
            'active_feature_max_step':float(abs(np.diff(masked,axis=0)).max())}
    record={'joint_names':d['joint_names'].tolist(),'groups':results,
            'scope':'Only specified task features vary; other inputs fixed at the 10s anchor. Not additive attribution.'}
    output.write_text(json.dumps(record,indent=2))
    for name,values in results.items():
        print(name,{joint:round(values['target_step_rms_deg'][record['joint_names'].index(joint)],5)
                    for joint in ('left_elbow_joint','right_elbow_joint')})


if __name__=='__main__':main()
