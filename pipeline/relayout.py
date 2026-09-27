import numpy as np,umap,glob
F=np.load('features.npy')
F=F+np.random.default_rng(3).normal(0,0.06,F.shape).astype(np.float32)
xy=umap.UMAP(n_neighbors=40,min_dist=0.55,spread=1.6,metric='euclidean',random_state=42).fit_transform(F)
old=glob.glob('dm_work/cache/layout_*.npz')[0]
np.savez_compressed(old,coords=xy.astype(np.float32))
print(xy.min(0),xy.max(0))
