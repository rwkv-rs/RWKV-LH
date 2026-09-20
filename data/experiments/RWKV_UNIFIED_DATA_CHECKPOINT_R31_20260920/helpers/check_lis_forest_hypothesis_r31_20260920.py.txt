import itertools
for n in range(1,9):
 best={}
 for p in itertools.permutations(range(1,n+1)):
  a=[]
  for i,x in enumerate(p):a.append(1+max((a[j] for j in range(i) if p[j]<x),default=0))
  b=[1]*n
  for i in range(n-1,-1,-1):b[i]=1+max((b[j] for j in range(i+1,n) if p[j]<p[i]),default=0)
  key=tuple(a);score=sum(b)
  if score>best.get(key,(-1,None))[0]:best[key]=(score,p)
 for a,(want,witness) in best.items():
  children=[[] for _ in range(n+1)];last=[0]*(n+1)
  for i,k in enumerate(a,1):children[last[k-1]].append(i);last[k]=i
  stack=children[0][:];p=[0]*n;value=0
  while stack:
   i=stack.pop();value+=1;p[i-1]=value;stack.extend(children[i])
  b=[1]*n
  for i in range(n-1,-1,-1):b[i]=1+max((b[j] for j in range(i+1,n) if p[j]<p[i]),default=0)
  if sum(b)!=want:print('counterexample',a,p,sum(b),want,witness);raise SystemExit(1)
 print('passed n',n,'families',len(best),flush=True)
