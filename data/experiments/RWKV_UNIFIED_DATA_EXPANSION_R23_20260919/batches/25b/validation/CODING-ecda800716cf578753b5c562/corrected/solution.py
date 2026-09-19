import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);m=next(v);g=[[] for i in range(n)]
 for i in range(m):
  a=next(v)-1;b=next(v)-1;c=next(v);g[a].append((b,c));g[b].append((a,c))
 value=[None]*n;ok=True
 for root in range(n):
  if value[root] is not None:continue
  value[root]=0;stack=[root]
  while stack:
   a=stack.pop()
   for b,c in g[a]:
    wanted=value[a]^c
    if value[b] is None:value[b]=wanted;stack.append(b)
    elif value[b]!=wanted:ok=False
 out.append('Yes' if ok else 'No')
print('\n'.join(out))
