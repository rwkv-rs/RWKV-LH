import sys
v=iter(sys.stdin.read().split());out=[]
while True:
 try:n=int(next(v))
 except StopIteration:break
 m=int(next(v));awake=set(next(v));g={chr(i):set() for i in range(65,91)}
 for i in range(m):
  edge=next(v);a,b=edge;g[a].add(b);g[b].add(a)
 years=0
 while len(awake)<n:
  new={a for a in g if a not in awake and len(g[a]&awake)>=3}
  if not new:break
  awake.update(new);years+=1
 out.append(f'WAKE UP IN, {years}, YEARS' if len(awake)>=n else 'THIS BRAIN NEVER WAKES UP')
print('\n'.join(out))
