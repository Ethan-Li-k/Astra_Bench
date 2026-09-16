from geom import *
from scipy.optimize import least_squares
from PIL import Image,ImageDraw
from itertools import product,combinations
import sys
import os
o=obs(os.environ.get("OBS"));old=json.load(open(ROOT/'box_fit.json'));p=old['parameters'];dims=np.array(p[3:6]);uv=np.array(json.loads(sys.argv[1]));sg=np.array([[-1,-1,1],[1,-1,1],[-1,-1,-1],[-1,1,-1]])
if len(sys.argv)>2:sg=np.array(json.loads(sys.argv[2]))
def pts(x,s=sg):return (s*dims/2)@Rot.from_euler('xyz',x[3:]).as_matrix().T+x[:3]
def fun(x):return np.concatenate([(proj(o,pts(x),s)-uv[s]).ravel() for s in (0,1)])
x=least_squares(fun,json.loads(sys.argv[3]) if len(sys.argv)>3 else p[:3]+[0,0,p[6]]).x
print('fit',x,'rms',np.sqrt(np.mean(fun(x)**2)),'residual',fun(x).reshape(2,len(sg),2).round(2))
fit={'parameters':x[:3].tolist()+dims.tolist()+[x[5]],'rotation_rpy':x[3:].tolist(),'source':'current stereo visible corners fixed RGB-derived dims; rounded-corner uncertainty +-4mm','observation':o['observation_id']};json.dump(fit,open(ROOT/'fit_candidate.json','w'))
for s in [0,1]:
 im=Image.open(o['images'][s]['path']);d=ImageDraw.Draw(im);pix=proj(o,pts(x,np.array(list(product([-1,1],repeat=3)))),s)
 for i,j in combinations(range(8),2):
  if bin(i^j).count('1')==1:d.line([tuple(pix[i]),tuple(pix[j])],fill='red',width=1)
 im.save(ROOT/f'refit_{s}.png')
