import sys,math
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);m=next(v);cost=[next(v) for _ in range(n)];neighbors=[[] for _ in range(n)]
 for j in range(m):
  a=next(v);b=next(v)-1;neighbors[b].append(a)
 groups={}
 for c,s in zip(cost,neighbors):
  if s:
   key=tuple(sorted(s));groups[key]=groups.get(key,0)+c
 g=0
 for x in groups.values():g=math.gcd(g,x)
 out.append(str(g))
print('\n'.join(out))
