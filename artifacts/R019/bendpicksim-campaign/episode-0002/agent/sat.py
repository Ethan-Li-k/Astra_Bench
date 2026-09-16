from geom import *
def gap_box(v,half):
 h=ConvexHull(v);norm=h.equations[:,:3];edges=set()
 for s in h.simplices:
  for i,j in [(0,1),(1,2),(2,0)]:edges.add(tuple(sorted([s[i],s[j]])))
 e=np.array([v[j]-v[i] for i,j in edges]);axes=np.r_[np.eye(3),norm,np.cross(e[:,None,:],np.eye(3)[None,:,:]).reshape(-1,3)];lens=np.linalg.norm(axes,axis=1);axes=axes[lens>1e-8]/lens[lens>1e-8,None];axes=np.unique(np.round(axes,5),axis=0);pv=v@axes.T;radius=np.abs(axes)@half;gaps=np.maximum(pv.min(0)-radius,-radius-pv.max(0));return gaps.max()
if __name__=='__main__':
 o=obs();f=json.load(open(ROOT/'box_fit.json'));p=f['parameters'];br=Rot.from_euler('xyz',f.get('rotation_rpy',[0,0,p[6]])).as_matrix();half=np.array(p[3:6])/2
 for b,v in meshes(o,'left').items():
  vb=(v-p[:3])@br;print(b,'signed SAT separation m',round(gap_box(vb,half),4),'margin4mm',round(gap_box(vb,half+.004),4))
