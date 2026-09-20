import sys
from fractions import Fraction
v=iter(map(int,sys.stdin.buffer.read().split()));output=[];case=0
for n in v:
 if n==0:break
 graph=[set() for _ in range(n)];reverse=[[] for _ in range(n)]
 while True:
  a=next(v);b=next(v)
  if a==b==0:break
  graph[a-1].add(b-1)
 for a in range(n):
  for b in graph[a]:reverse[b].append(a)
 reached={0};todo=[0]
 for a in todo:
  for b in graph[a]:
   if b not in reached:reached.add(b);todo.append(b)
 visited=set();order=[]
 def dfs(a):
  visited.add(a)
  for b in graph[a]:
   if b not in visited:dfs(b)
  order.append(a)
 for a in reached:
  if a not in visited:dfs(a)
 component={};groups=[]
 for a in reversed(order):
  if a in component:continue
  cid=len(groups);group=[a];component[a]=cid
  for u in group:
   for b in reverse[u]:
    if b in reached and b not in component:component[b]=cid;group.append(b)
  groups.append(group)
 infinite=set()
 for cid,group in enumerate(groups):
  if any(graph[a] for a in group) and all(component[b]==cid for a in group for b in graph[a]):infinite.update(group)
 finite=sorted(reached-infinite);index={a:i for i,a in enumerate(finite)};size=len(finite);matrix=[[0]*(size+1) for _ in range(size)]
 for a,i in index.items():
  matrix[i][i]=max(1,len(graph[a]));matrix[i][-1]=int(a==0)
  for b in graph[a]:
   if b in index:matrix[index[b]][i]-=1
 previous=1
 for k in range(size-1):
  if matrix[k][k]==0:
   pivot=next(i for i in range(k+1,size) if matrix[i][k]);matrix[k],matrix[pivot]=matrix[pivot],matrix[k]
  pivot=matrix[k][k];row=matrix[k]
  for i in range(k+1,size):
   target=matrix[i];factor=target[k]
   for j in range(k+1,size+1):target[j]=(target[j]*pivot-factor*row[j])//previous
   target[k]=0
  previous=pivot
 solution=[Fraction(0)]*size
 for i in range(size-1,-1,-1):solution[i]=(Fraction(matrix[i][-1])-sum(matrix[i][j]*solution[j] for j in range(i+1,size)))/matrix[i][i]
 case+=1;output.append(f'Case #{case}:');q=next(v)
 for _ in range(q):
  a=next(v)-1
  if a in infinite:output.append('infinity')
  elif a not in index:output.append('0.000')
  else:
   value=solution[index[a]]*max(1,len(graph[a]));whole,remainder=divmod(value.numerator*1000,value.denominator)
   if 2*remainder>value.denominator or (2*remainder==value.denominator and whole&1):whole+=1
   output.append(f'{whole//1000}.{whole%1000:03d}')
print('\n'.join(output))
