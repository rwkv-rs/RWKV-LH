from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
101:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
while True:
 try:n=next(it)
 except StopIteration:break
 if not n:break
 d=[[next(it) for _ in range(n)] for _ in range(n)];g={i:{} for i in range(n)};nextid=n
 def edge(a,b,w):g[a][b]=w;g[b][a]=w
 def build(count):
  global nextid
  if count==2:edge(0,1,d[0][1]);return
  if count<2:return
  leaf=count-1;limb=min((d[i][leaf]+d[j][leaf]-d[i][j])//2 for i in range(leaf) for j in range(i+1,leaf))
  pair=next((i,j) for i in range(leaf) for j in range(i+1,leaf) if d[i][leaf]+d[j][leaf]-2*limb==d[i][j]);start,end=pair;distance=d[start][leaf]-limb;build(leaf);parents={start:None};stack=[start]
  for x in stack:
   if x==end:break
   for y in g[x]:
    if y not in parents:parents[y]=x;stack.append(y)
  path=[end]
  while path[-1]!=start:path.append(parents[path[-1]])
  path.reverse();attach=start
  for a,b in zip(path,path[1:]):
   if distance==0:attach=a;break
   w=g[a][b]
   if distance<w:
    attach=nextid;nextid+=1;g[attach]={};del g[a][b];del g[b][a];edge(a,attach,distance);edge(attach,b,w-distance);break
   distance-=w;attach=b
  edge(attach,leaf,limb)
 build(n);degrees=[];twos=0
 for x,neighbors in g.items():
  if x>=n:degrees.append(len(neighbors))
  for y,w in neighbors.items():
   if x<y:twos+=w-1
 degrees.extend([2]*twos);degrees.sort();out.append(' '.join(map(str,degrees)))
print('\\n'.join(out))
''','Additive phylogeny reconstructs weighted branch edges; each edge of integer length w contributes w-1 degree-two internal vertices.'),
110:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);events=[]
for _ in range(n):
 count=next(it);p=[(next(it),next(it)) for _ in range(count)];area=sum(p[i][0]*p[(i+1)%count][1]-p[i][1]*p[(i+1)%count][0] for i in range(count));orientation=1 if area>0 else -1
 for i in range(count):
  x,y=p[i];u,v=p[(i+1)%count]
  if x==u:events.append((x,min(y,v),max(y,v),-orientation*(1 if v>y else -1)))
events.sort();q=next(it);queries=sorted((next(it),next(it),i) for i in range(q));size=100002;bit=[0]*(size+1);answer=[0]*q;pos=0
def add(y,value):
 y+=1
 while y<=size:bit[y]+=value;y+=y&-y
for x,y,i in queries:
 while pos<len(events) and events[pos][0]<=x:
  _,low,high,value=events[pos];add(low,value);add(high,-value);pos+=1
 y+=1;total=0
 while y:total+=bit[y];y-=y&-y
 answer[i]=total
print('\\n'.join(map(str,answer)))
''','Sweep vertical polygon boundaries with orientation-aware signed interval updates; Fenwick prefix values count polygons covering query cell centers.'),
113:('''import sys,bisect
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);orders=[]
 for _ in range(n):
  start=next(it);duration=next(it);price=next(it);orders.append((start+duration,start,price))
 orders.sort();ends=[];dp=[0]
 for end,start,price in orders:
  earlier=bisect.bisect_right(ends,start);dp.append(max(dp[-1],dp[earlier]+price));ends.append(end)
 out.append(str(dp[-1]))
print('\\n'.join(out))
''','Weighted interval scheduling sorted by end time; binary search finds the last compatible predecessor.'),
114:('''import sys
n,m=map(int,sys.stdin.buffer.readline().split());grid=[sys.stdin.buffer.readline().strip() for _ in range(n)];cells=[(r,c) for r in range(n) for c in range(m) if grid[r][c]==46];index={cell:i for i,cell in enumerate(cells)};size=len(cells)
if size<=1:print(1);raise SystemExit
matrix=[[0]*size for _ in range(size)]
for i,(r,c) in enumerate(cells):
 for neighbor in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
  j=index.get(neighbor)
  if j is not None:matrix[i][i]+=1;matrix[i][j]-=1
matrix=[row[:-1] for row in matrix[:-1]];size-=1;previous=1;sign=1
for k in range(size-1):
 if matrix[k][k]==0:
  pivot=next((i for i in range(k+1,size) if matrix[i][k]),None)
  if pivot is None:print(0);raise SystemExit
  matrix[k],matrix[pivot]=matrix[pivot],matrix[k];sign=-sign
 pivot=matrix[k][k]
 for i in range(k+1,size):
  factor=matrix[i][k]
  for j in range(k+1,size):matrix[i][j]=(matrix[i][j]*pivot-factor*matrix[k][j])//previous
  matrix[i][k]=0
 previous=pivot
print(sign*matrix[-1][-1]%1000000000)
''','Matrix-tree theorem and fraction-free Bareiss determinant avoid invalid modular division under composite modulus 1e9.'),
115:('''import sys
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
print('\\n'.join(out))
''','Number of directed length-four walks is the sum of squared length-two walk counts from each midpoint; difference between adjacent weight thresholds.'),
119:('''import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];b=v[n+1:];heap=[(-b[i],i) for i in range(n) if b[i]>a[i]];heapq.heapify(heap);answer=0
if any(x<y for x,y in zip(b,a)):print(-1);raise SystemExit
while heap:
 neg,i=heapq.heappop(heap)
 if -neg!=b[i] or b[i]==a[i]:continue
 step=b[(i-1)%n]+b[(i+1)%n];count=(b[i]-a[i])//step
 if count==0:print(-1);raise SystemExit
 b[i]-=count*step;answer+=count
 if b[i]>a[i]:heapq.heappush(heap,(-b[i],i))
print(answer)
''','Reverse the largest pending value; batch as many neighbor-sum subtractions as allowed without going below its target.'),
121:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);queries=[(next(it),next(it)) for _ in range(t)];groups={};mod=1000000007
for n,k in queries:groups[k]=max(groups.get(k,0),n)
answers={}
for k,maximum in groups.items():
 result=[1]+[0]*maximum
 if k==1:answers[k]=result;continue
 for length in range(1,min(maximum,k-1)+1):result[length]=pow(2,length,mod)
 if maximum<k:answers[k]=result;continue
 def palindrome(x,length):return all(((x>>j)^(x>>(length-1-j)))&1==0 for j in range(length//2))
 size=1<<k;mask=size-1;valid=[x for x in range(size) if not palindrome(x,k)];dp=[0]*size;edges={}
 for x in valid:
  dp[x]=1;edges[x]=[y for bit in (0,1) if not palindrome((x<<1)|bit,k+1) and not palindrome((y:=((x<<1)|bit)&mask),k)]
 result[k]=sum(dp)
 for length in range(k+1,maximum+1):
  nxt=[0]*size
  for x in valid:
   if dp[x]:
    for y in edges[x]:nxt[y]=(nxt[y]+dp[x])%mod
  dp=nxt;result[length]=sum(dp)%mod
 answers[k]=result
print('\\n'.join(str(answers[k][n]) for n,k in queries))
''','Any forbidden palindrome contains one of lengths k or k+1; suffix-mask DP excludes both and shares precomputation across queries.'),
122:('''import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);values=[next(it) for _ in range(n)];source=n;sink=n+1;g=[[] for _ in range(n+2)]
def add(a,b,cap):g[a].append([b,cap,len(g[b])]);g[b].append([a,0,len(g[a])-1])
positive=0
for i,v in enumerate(values):
 if v>0:add(source,i,v);positive+=v
 elif v<0:add(i,sink,-v)
for _ in range(m):add(next(it)-1,next(it)-1,next(it))
flow=0
while True:
 level=[-1]*(n+2);level[source]=0;q=deque([source])
 while q:
  x=q.popleft()
  for y,cap,rev in g[x]:
   if cap and level[y]<0:level[y]=level[x]+1;q.append(y)
 if level[sink]<0:break
 current=[0]*(n+2)
 def send(x,limit):
  if x==sink:return limit
  while current[x]<len(g[x]):
   edge=g[x][current[x]];y,cap,rev=edge
   if cap and level[y]==level[x]+1:
    amount=send(y,min(limit,cap))
    if amount:edge[1]-=amount;g[y][rev][1]+=amount;return amount
   current[x]+=1
  return 0
 while True:
  amount=send(source,10**18)
  if not amount:break
  flow+=amount
print(positive-flow)
''','Maximum profit equals positive scores minus minimum s-t cut; each directed dependency becomes its penalty-capacity edge.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2));shutil.copytree(p,D/'upload/tasks'/rows[i]['id']/p.name,dirs_exist_ok=True)
