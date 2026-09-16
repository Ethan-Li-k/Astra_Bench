from geom import *
from PIL import Image
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
idx=int(sys.argv[1]);o=obs(idx);polys=[]
for im in o['images']:
 a=np.array(Image.open(im['path']));yy,xx=np.indices(a.shape[:2]);m=(a.min(2)>225)&(a.max(2)-a.min(2)<15)&(xx>265)&(xx<355)&(yy>215)&(yy<280);pts=np.c_[xx[m],yy[m]];h=pts[ConvexHull(pts).vertices];print(im['camera'],'hull',h.tolist());polys.append(h)
