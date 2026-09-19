import sys
v=sys.stdin.read().split();s=v[0];t=v[1];table=list(map(int,v[2:18]));opening,extension=map(int,v[18:20]);index={c:i for i,c in enumerate('ATGC')};n=len(t);neg=-10**30
best=[0]+[-opening-extension*(j-1) for j in range(1,n+1)];vertical=[neg]*(n+1)
for i,x in enumerate(s,1):
 current=[-opening-extension*(i-1)]+[neg]*n;newvertical=[neg]*(n+1);horizontal=neg
 for j,y in enumerate(t,1):
  newvertical[j]=max(best[j]-opening,vertical[j]-extension)
  horizontal=max(current[j-1]-opening,horizontal-extension)
  current[j]=max(best[j-1]+table[4*index[x]+index[y]],newvertical[j],horizontal)
 best,vertical=current,newvertical
print(best[-1])
