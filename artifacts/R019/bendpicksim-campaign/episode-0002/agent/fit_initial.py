from geom import *
from scipy.optimize import least_squares
from itertools import product
from PIL import Image, ImageDraw
o=obs(EP/'observations/0000/observation.json')
uv=np.array([[[257,213],[486,220],[272,169],[474,176],[270,331],[442,338]],[[188,213],[416,220],[209,169],[410,176],[216,331],[388,338]]])
# Near x face: y+ top,y- top; far x face top; near face bottoms.
sg=np.array([[-1,1,1],[-1,-1,1],[1,1,1],[1,-1,1],[-1,1,-1],[-1,-1,-1]])
def corners(p,signs=sg):return (signs*np.array(p[3:6])/2)@Rot.from_euler('z',p[6]).as_matrix().T+p[:3]
def fun(p):return np.concatenate([(proj(o,corners(p),s)-uv[s]).ravel() for s in (0,1)])
p=least_squares(fun,[-.265,-.025,.865,.06,.16,.21,0]).x
print('FIT',p,'residual',fun(p).reshape(2,6,2).round(2),'rms',np.sqrt(np.mean(fun(p)**2)))
json.dump({'parameters':p.tolist(),'source':'manually visible stereo corners with rounded edges; approximate +-4mm','observation':'0000'},open(ROOT/'box_fit.json','w'))
pts=corners(p,np.array(list(product([-1,1],repeat=3))))
for s in (0,1):
 im=Image.open(o['images'][s]['path']);d=ImageDraw.Draw(im);pix=proj(o,pts,s)
 for i,j in __import__('itertools').combinations(range(8),2):
  if bin(i^j).count('1')==1:d.line([tuple(pix[i]),tuple(pix[j])],fill='red',width=1)
 im.save(ROOT/f'fit_initial_{s}.png')
for n,v in meshes(o,'left').items():print(n,np.round(v.min(0),3),np.round(v.max(0),3))
