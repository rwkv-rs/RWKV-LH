import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=1;out=[]
for case in range(1,v[0]+1):
 n,m=v[p:p+2];p+=2;reach=[1<<i for i in range(n)];edges=[]
 for _ in range(m):a,b=v[p]-1,v[p+1]-1;p+=2;reach[a]|=1<<b;edges.append((a,b))
 for k in range(n):
  bit=1<<k;row=reach[k]
  for i in range(n):
   if reach[i]&bit:reach[i]|=row
 groups={};component=[];sizes=[];representatives=[]
 for i,row in enumerate(reach):
  if row not in groups:groups[row]=len(sizes);sizes.append(0);representatives.append(i)
  c=groups[row];sizes[c]+=1;component.append(c)
 graph=[set() for _ in sizes]
 for a,b in edges:
  if component[a]!=component[b]:graph[component[a]].add(component[b])
 minimum=sum(s for s in sizes if s>1);maximum=sum(row.bit_count()-1 for row in reach)
 for children in graph:
  covered=0
  for c in sorted(children,key=lambda x:reach[representatives[x]].bit_count(),reverse=True):
   representative=representatives[c]
   if not covered>>representative&1:minimum+=1;covered|=reach[representative]
 out.append(f'Case #{case}: {minimum} {maximum}')
print('\n'.join(out))
