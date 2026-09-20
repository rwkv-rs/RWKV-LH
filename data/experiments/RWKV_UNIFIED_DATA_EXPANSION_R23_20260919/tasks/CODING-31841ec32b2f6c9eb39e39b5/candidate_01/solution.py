import sys,itertools,functools
values=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for n in values:
 if n==0:break
 m=next(values);need=[n//2]*n;known=set()
 for _ in range(m):
  u=next(values)-1;v=next(values)-1;need[u]-=1;known.add((min(u,v),max(u,v)))
 future=[[v for v in range(u+1,n) if (u,v) not in known] for u in range(n)]
 choices=[]
 for u in range(n):
  neighbors=future[u];choices.append([[tuple(v-u-1 for v in lost) for lost in itertools.combinations(neighbors,len(neighbors)-wins)] for wins in range(len(neighbors)+1)])
 @functools.lru_cache(None)
 def solve(u,remaining):
  if u==n:return 1
  k=remaining[0]
  if k<0 or k>len(future[u]):return 0
  answer=0
  for lost in choices[u][k]:
   after=list(remaining[1:]);valid=True
   for v in lost:
    after[v]-=1
    if after[v]<0:valid=False;break
   if valid:answer+=solve(u+1,tuple(after))
  return answer
 out.append(str(solve(0,tuple(need))))
print('\n'.join(out))
