import itertools
for n in range(1,9):
 cache={}
 for p in itertools.permutations(range(1,n+1)):
  a=[]
  for i,x in enumerate(p):a.append(1+max((a[j] for j in range(i) if p[j]<x),default=0))
  key=tuple(a)
  if key not in cache:
   children=[[] for _ in range(n+1)];last=[0]*(n+1)
   for i,k in enumerate(a,1):children[last[k-1]].append(i);last[k]=i
   stack=children[0][:];c=[0]*n;value=0
   while stack:
    i=stack.pop();value+=1;c[i-1]=value;stack.extend(children[i])
   cache[key]=c
  c=cache[key]
  for i in range(n):
   for j in range(i+1,n):
    if p[i]>p[j] and c[i]<c[j]:print('counterexample',key,p,c,i,j);raise SystemExit(1)
 print('passed inversion n',n,flush=True)
