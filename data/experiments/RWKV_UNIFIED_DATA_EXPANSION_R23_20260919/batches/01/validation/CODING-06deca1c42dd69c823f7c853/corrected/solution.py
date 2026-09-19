import sys
sys.setrecursionlimit(1000000)
f=sys.stdin.buffer;out=[]
while True:
 line=f.readline()
 if not line:break
 if not line.strip():continue
 n,m=map(int,line.split());rules=[]
 for _ in range(m):
  p=f.readline().replace(b':',b' ').split();a=int(p[0])-1;b=int(p[2])-1;u=2*a+(p[1]==b'right');v=2*b+(p[3]==b'right');rules.append((a,b,u,v))
 def feasible(h):
  size=2*(h-1)
  if not size:return True
  g=[[] for _ in range(size)];rev=[[] for _ in range(size)]
  for a,b,u,v in rules:
   if a<h-1 and b<h-1:
    g[u].append(v^1);rev[v^1].append(u);g[v].append(u^1);rev[u^1].append(v)
  seen=bytearray(size);order=[]
  def visit(v):
   seen[v]=1
   for w in g[v]:
    if not seen[w]:visit(w)
   order.append(v)
  for v in range(size):
   if not seen[v]:visit(v)
  comp=[-1]*size
  for v in reversed(order):
   if comp[v]>=0:continue
   comp[v]=v;stack=[v]
   while stack:
    z=stack.pop()
    for w in rev[z]:
     if comp[w]<0:comp[w]=v;stack.append(w)
  return all(comp[i]!=comp[i^1] for i in range(0,size,2))
 lo,hi=1,n
 while lo<hi:
  mid=(lo+hi+1)//2
  if feasible(mid):lo=mid
  else:hi=mid-1
 out.append(str(lo))
print('\n'.join(out))
