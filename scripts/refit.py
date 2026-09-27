"""Re-epoch every satellite to a common reference time T0 using full SGP4, so the in-browser
Kepler+J2 propagator matches SGP4 closely for days around T0 (captures drag + mean-motion recovery)."""
import json,math,datetime as dt
from sgp4.api import Satrec,jday
from sgp4 import omm
def u_of(r,W,inc):
  x,y,z=r;return math.atan2(z/math.sin(inc) if abs(math.sin(inc))>1e-6 else (-x*math.sin(W)+y*math.cos(W)), x*math.cos(W)+y*math.sin(W))
def model(el,tsec):
  a,e,inc,W0,Wd,w0,wd,M0,Md=el;W=W0+Wd*tsec;w=w0+wd*tsec;M=M0+Md*tsec;E=M
  for _ in range(12):E=E-(E-e*math.sin(E)-M)/(1-e*math.cos(E))
  xp=a*(math.cos(E)-e);yp=a*math.sqrt(1-e*e)*math.sin(E)
  cW,sW,cw,sw,ci,si=math.cos(W),math.sin(W),math.cos(w),math.sin(w),math.cos(inc),math.sin(inc)
  return (xp*(cW*cw-sW*sw*ci)-yp*(cW*sw+sW*cw*ci),xp*(sW*cw+cW*sw*ci)+yp*(cW*cw*ci-sW*sw),xp*(sw*si)+yp*(cw*si)),W
def wrap(x):return (x+math.pi)%(2*math.pi)-math.pi
def refit(o,T0,span=86400):
  s=Satrec();omm.initialize(s,o);RE=s.radiusearthkm
  def sg(t):
    d=dt.datetime.fromtimestamp(t,dt.timezone.utc);jd,fr=jday(d.year,d.month,d.day,d.hour,d.minute,d.second+d.microsecond/1e6)
    e,r,v=s.sgp4(jd,fr);return None if e else r
  ep=(s.jdsatepoch-2440587.5+s.jdsatepochF)*86400;dt0=T0-ep
  a=s.a*RE;e=s.ecco;inc=s.inclo
  el=[a,e,inc,s.nodeo+s.nodedot*dt0/60,s.nodedot/60,s.argpo+s.argpdot*dt0/60,s.argpdot/60,(s.mo+s.mdot*dt0/60)%(2*math.pi),s.mdot/60]
  r0,r1=sg(T0),sg(T0+span)
  if r0 is None or r1 is None: return el,False
  m0,W0=model(el,0);m1,W1=model(el,span)
  d0=wrap(u_of(r0,W0,inc)-u_of(m0,W0,inc));d1=wrap(u_of(r1,W1,inc)-u_of(m1,W1,inc))
  el[7]=(el[7]+d0)%(2*math.pi);el[8]+= (d1-d0)/span   # assumes |drift|<pi per day
  return el,True
