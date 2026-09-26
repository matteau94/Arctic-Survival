import sys, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
exec(open('val.py').read().split("sx,sy = SPAWN")[0])
from terrain import mountains as M, ocean
t=np.arange(-2400e3,2400e3,8000.0); X,Y=np.meshgrid(t,t); base,land=ocean.continent(X,Y)
F=M._macro(X.ravel(),Y.ravel()); amp=F[:,M._F_AMP].reshape(X.shape)/M.PEAK_GAIN; nd=F[:,M._F_ND].reshape(X.shape)
L=land>0.5; print("continent: land frac with range amp>300m: %.1f%%, amp>1500: %.1f%%, nunatak density>0.05: %.1f%%" % (100*(amp[L]>300).mean(), 100*(amp[L]>1500).mean(), 100*(nd[L]>0.05).mean()))
img=np.dstack([np.clip(amp/4000*255,0,255), np.clip(nd*200,0,255), np.where(land>0,70,20)+0*amp])
sx_,sy_=((np.array(SPAWN)+2400e3)/8000).astype(int); img[sy_-3:sy_+4,sx_-3:sx_+4]=[255,255,255]
png('continent.png', img[::-1])
