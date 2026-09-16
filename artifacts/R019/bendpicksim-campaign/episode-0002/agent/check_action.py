from geom import *
from sat import gap_box
from scipy.spatial.transform import Slerp
a=json.load(open(ROOT/'action.json'));o=json.load(open(a['observation_path']));n='left_wrist_yaw_link';wp=np.array(o['four_point_world'][n]['position_world_m']);wr=R(o['four_point_world'][n]['quaternion_wxyz']);target=a['response']['trajectory'][-1]['target'][n];tp=np.array(target['position_world_m']);rv=Rot.from_matrix(R(target['quaternion_wxyz'])@wr.T).as_rotvec();fit=json.load(open(ROOT/'box_fit.json'));p=fit['parameters'];br=Rot.from_euler('xyz',fit.get('rotation_rpy',[0,0,p[6]])).as_matrix();half=np.array(p[3:6])/2;out={}
for b,v in meshes(o,'left').items():
 vals=[]
 for f in np.linspace(0,1,11):
  w=(v-wp)@Rot.from_rotvec(rv*f).as_matrix().T+wp+(tp-wp)*f;vb=(w-p[:3])@br;bound=np.maximum(vb.min(0)-half-.004,-half-.004-vb.max(0)).max();g=gap_box(vb,half+.004) if bound<.01 else bound;vals.append((g,f,w[:,2].min()))
 out[b]=min(vals)
print('swept SAT margin4mm',out)
