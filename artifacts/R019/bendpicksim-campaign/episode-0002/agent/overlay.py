from geom import *
from itertools import product,combinations
from PIL import Image,ImageDraw
o=obs();p=json.load(open(ROOT/'box_fit.json'))['parameters'];pts=np.array(list(product([-1,1],repeat=3)))*np.array(p[3:6])/2;pts=pts@Rot.from_euler('xyz',json.load(open(ROOT/'box_fit.json')).get('rotation_rpy',[0,0,p[6]])).as_matrix().T+p[:3]
for s in [0,1]:
 im=Image.open(o['images'][s]['path']);d=ImageDraw.Draw(im);pix=proj(o,pts,s)
 for i,j in combinations(range(8),2):
  if bin(i^j).count('1')==1:d.line([tuple(pix[i]),tuple(pix[j])],fill='red',width=1)
 im.save(ROOT/f'overlay_{s}.png')
