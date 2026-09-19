import sys
a=list(map(int,sys.stdin.buffer.read().split()));n=a[0];p=[(a[2*i+1]&1,a[2*i+2]&1) for i in range(n)]
pref=[0]*n
for i in range(1,n):
 x,y=p[i-1];u,v=p[i];pref[i]=pref[i-1]^((x*v-y*u)&1)
x,y=p[-1];u,v=p[0]
if pref[-1]^((x*v-y*u)&1):print(0)
else:
 count=[[[0]*2 for _ in range(2)] for _ in range(2)];ans=0
 for j,(x,y) in enumerate(p):
  for u in range(2):
   for v in range(2):ans+=count[u][v][pref[j]^((x*v-y*u)&1)]
  count[x][y][pref[j]]+=1
 print(ans-n)
