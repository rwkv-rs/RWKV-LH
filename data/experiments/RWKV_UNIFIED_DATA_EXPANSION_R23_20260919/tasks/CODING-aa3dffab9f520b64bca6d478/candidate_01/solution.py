import sys,math
v=sys.stdin.buffer.read().split();p=0;out=[]
while p<len(v):
 n=int(v[p]);p+=1;points=[];zmax=0.0
 for _ in range(n):x,y,z=map(float,v[p:p+3]);p+=3;points.append((math.hypot(x,y),z));zmax=max(zmax,z)
 def radius(h):return max(r*h/(h-z) for r,z in points)
 def objective(h):r=radius(h);return r*r*h
 low=zmax;high=3*zmax
 for _ in range(140):
  a=(2*low+high)/3;b=(low+2*high)/3
  if objective(a)<=objective(b):high=b
  else:low=a
 h=(low+high)/2;out.append('%.3f %.3f'%(h,radius(h)))
print('\n'.join(out))
