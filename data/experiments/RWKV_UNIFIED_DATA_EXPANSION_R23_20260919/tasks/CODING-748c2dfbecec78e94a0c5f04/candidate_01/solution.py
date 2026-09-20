import sys,bisect
it=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(it),next(it);a=[next(it) for _ in range(n)];positions={}
for i,c in enumerate(a):positions.setdefault(c,[]).append(i)
out=[]
for _ in range(m):
 t=next(it)
 if t==1:
  l,r,c=next(it)-1,next(it)-1,next(it);p=positions.get(c,());out.append(str(bisect.bisect_right(p,r)-bisect.bisect_left(p,l)))
 else:
  x=next(it)-1;u,v=a[x],a[x+1]
  if u!=v:
   pu,pv=positions[u],positions[v];pu[bisect.bisect_left(pu,x)]=x+1;pv[bisect.bisect_left(pv,x+1)]=x;a[x],a[x+1]=v,u
print('\n'.join(out))
