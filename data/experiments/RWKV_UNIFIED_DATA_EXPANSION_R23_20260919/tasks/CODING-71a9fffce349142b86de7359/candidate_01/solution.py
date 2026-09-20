import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));pairs=list(zip(v[1::2],v[2::2]));maximum=max((max(a,b) for a,b in pairs),default=1);f=[1,2]
while f[-1]<maximum:f.append(f[-1]+f[-2])
out=[]
for a,b in pairs:
 while a!=b:
  if a<b:a,b=b,a
  a-=f[bisect.bisect_left(f,a)-1]
 out.append(str(a))
print('\n'.join(out))
