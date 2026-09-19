import sys
v=list(map(int,sys.stdin.buffer.read().split()));m,k=v[:2];roads=v[2:2+m];supply=v[2+m:2+2*m];fuel=0;best=0;waits=0
for d,s in zip(roads,supply):
 fuel+=s;best=max(best,s)
 if fuel<d:
  extra=(d-fuel+best-1)//best;waits+=extra;fuel+=extra*best
 fuel-=d
print(sum(roads)+k*waits)
