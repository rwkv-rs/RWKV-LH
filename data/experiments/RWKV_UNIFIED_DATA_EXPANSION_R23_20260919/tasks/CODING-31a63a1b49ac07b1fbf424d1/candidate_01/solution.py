import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,h=v[:2];dp={0:1};mod=1000000007
for a in v[2:2+n]:
 d=h-a;new={}
 for opened,ways in dp.items():
  if d!=opened and d!=opened+1:continue
  new[d]=(new.get(d,0)+ways)%mod
  if d>0:new[d-1]=(new.get(d-1,0)+ways*d)%mod
 dp=new
print(dp.get(0,0))
