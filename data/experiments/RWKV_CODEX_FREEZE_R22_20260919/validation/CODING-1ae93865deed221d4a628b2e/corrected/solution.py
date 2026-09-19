import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);groups=[[] for _ in range(101)]
for _ in range(m):
 a=next(it)-1;b=next(it)-1;w=next(it);groups[w].append((a,b))
degree=[0]*n;edges=[];totals=[0]*101
for w in range(1,101):
 for a,b in groups[w]:degree[a]+=1;degree[b]+=1;edges.append((a,b))
 paths=[0]*n
 for a,b in edges:paths[a]+=degree[b];paths[b]+=degree[a]
 totals[w]=sum(x*x for x in paths)
out=[]
for _ in range(next(it)):
 x=next(it);out.append(str(totals[x]-totals[x-1]))
print('\n'.join(out))
