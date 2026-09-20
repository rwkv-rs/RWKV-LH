import sys
values=iter(map(int,sys.stdin.buffer.read().split()));output=[]
for _ in range(next(values)):
 n=next(values);x=next(values);y=next(values)
 if x>=(1<<n) or y>=(1<<n):output.append('0');continue
 dp={(0,0):1}
 for bit in range(n):
  xb=(x>>bit)&1;yb=(y>>bit)&1;following={}
  for (cx,cy),ways in dp.items():
   for u,v in ((0,0),(1,0),(1,1)):
    a=u+xb+cx;b=v+yb+cy
    if (a&1)==0 and (b&1)==1:continue
    key=(a>>1,b>>1);following[key]=following.get(key,0)+ways
  dp=following
 output.append(str(dp.get((0,0),0)))
print('\n'.join(output))
