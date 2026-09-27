import numpy as np,json,glob,collections,sys
L=np.load(glob.glob('dm_work/cache/layout_*.npz')[0]); C=np.load(glob.glob('dm_work/cache/clusters_*.npz')[0])
R=json.load(open('master.json')); xy=L['coords']
for li in range(3):
  lab=C[f'layer_{li}']; ids=sorted(set(lab)-{-1}); print('LAYER',li,len(ids),'noise',round(float(np.mean(lab==-1)),3))
  for cid in ids:
    idx=np.where(lab==cid)[0]; rs=[R[i] for i in idx]
    def top(f,k=3): return [(a,b) for a,b in collections.Counter(f(r) for r in rs).most_common(k)]
    c=xy[idx].mean(0)
    print(cid,len(idx),'xy=%.1f,%.1f'%tuple(c),top(lambda r:r.get('const_name') or r.get('kind')),
      top(lambda r:r.get('shell') if r['e']==0 else (r['network'] if r['kind']!='SatNOGS station' else '%s %s'%(r['status'],('N.Am' if -170<r['lon']<-50 and r['lat']>10 else 'S.Am' if r['lon']<-30 else 'Europe' if r['lon']<45 and r['lat']>35 else 'Africa/ME' if r['lon']<60 else 'Asia' if r['lat']>0 else 'Oceania'))),3),
      top(lambda r:r.get('year'),2))
