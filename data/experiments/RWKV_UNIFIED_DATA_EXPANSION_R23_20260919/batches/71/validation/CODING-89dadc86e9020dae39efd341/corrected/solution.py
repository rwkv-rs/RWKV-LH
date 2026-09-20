import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));p=1;out=[]
for _ in range(v[0]):
 n,w=v[p:p+2];p+=2;a=sorted(v[p:p+n],reverse=True);p+=n;prefix=[0]
 for x in a:prefix.append(prefix[-1]+x)
 old=[0]+[None]*n
 for groups in range(1,min(w,n)+1):
  new=[None]*(n+1);hull=deque()
  for i in range(groups,n+1):
   t=i-1
   if old[t] is not None:
    line=(-prefix[t],old[t])
    while len(hull)>1:
     a0,b0=hull[-2];a1,b1=hull[-1];a2,b2=line
     if (b1-b0)*(a1-a2)>=(b2-b1)*(a0-a1):hull.pop()
     else:break
    hull.append(line)
   while len(hull)>1 and hull[0][0]*i+hull[0][1]>=hull[1][0]*i+hull[1][1]:hull.popleft()
   if hull:new[i]=i*prefix[i]+hull[0][0]*i+hull[0][1]
  old=new
 out.append(f'{old[n]/prefix[n]:.4f}')
print('\n'.join(out))
