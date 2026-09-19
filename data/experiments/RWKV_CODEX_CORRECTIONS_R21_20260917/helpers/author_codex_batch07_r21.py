from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
80:('''import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];limit=math.isqrt(max(a));sieve=bytearray(b'\\1')*(limit+1);primes=[]
for p in range(2,limit+1):
 if sieve[p]:
  primes.append(p)
  if p*p<=limit:sieve[p*p::p]=b'\\0'*((limit-p*p)//p+1)
best={};cached={};answer=0
for x in a:
 divisors=cached.get(x)
 if divisors is None:
  divisors=[1];y=x
  for p in primes:
   if p*p>y:break
   if y%p==0:
    old=divisors[:];power=1
    while y%p==0:y//=p;power*=p;divisors.extend(d*power for d in old)
  if y>1:divisors.extend([d*y for d in divisors])
  cached[x]=divisors
 value=max(best.get(d,0) for d in divisors)+1;best[x]=value;answer=max(answer,value)
print(answer)
''','Prefix DP keyed by endpoint value; factor each distinct value and enumerate its divisors instead of checking all prior positions.'),
81:('''import sys,itertools,collections,functools
vertices=list(itertools.product((-1,1),repeat=3));edges=[(a,b) for a in vertices for b in vertices if a<b and sum(x!=y for x,y in zip(a,b))==1];lookup={edge:i for i,edge in enumerate(edges)};types=collections.Counter()
for perm in itertools.permutations(range(3)):
 parity=(-1)**sum(perm[i]>perm[j] for i in range(3) for j in range(i+1,3))
 for signs in itertools.product((-1,1),repeat=3):
  if parity*signs[0]*signs[1]*signs[2]!=1:continue
  mapping=[]
  for a,b in edges:
   aa=tuple(signs[i]*a[perm[i]] for i in range(3));bb=tuple(signs[i]*b[perm[i]] for i in range(3));mapping.append(lookup[tuple(sorted((aa,bb)))])
  seen=set();cycles=[]
  for i in range(12):
   if i in seen:continue
   length=0
   while i not in seen:seen.add(i);length+=1;i=mapping[i]
   cycles.append(length)
  types[tuple(sorted(cycles,reverse=True))]+=1
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for test in range(v[0]):
 counts=tuple(collections.Counter(v[1+12*test:13+12*test]).values());total=0
 for cycles,multiple in types.items():
  @functools.lru_cache(None)
  def fixed(i,left):
   if i==len(cycles):return 1
   length=cycles[i];answer=0
   for j,num in enumerate(left):
    if num>=length:changed=list(left);changed[j]-=length;answer+=fixed(i+1,tuple(changed))
   return answer
  total+=multiple*fixed(0,counts)
 out.append(str(total//24))
print('\\n'.join(out))
''','Burnside over the 24 proper cube rotations; assign monochromatic edge cycles respecting exact color multiplicities.'),
82:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];x=sorted(v[1:n+1]);prefix=[0]
for value in x:prefix.append(prefix[-1]+value)
out=[]
for i in range(v[n+1]):
 a,b=v[n+2+2*i:n+4+2*i];index=(b*n-1)//(a+b);y=x[index];out.append(str(a*(y*index-prefix[index])+b*(prefix[n]-prefix[index+1]-y*(n-index-1))))
print('\\n'.join(out))
''','Asymmetric absolute loss is minimized at the b/(a+b) quantile; prefix sums evaluate its cost.'),
83:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);m=next(it);g=[[] for _ in range(n)];rev=[[] for _ in range(n)];edges=[]
 for _ in range(m):
  a=next(it)-1;b=next(it)-1;g[a].append(b);rev[b].append(a);edges.append((a,b))
 seen=bytearray(n);order=[]
 for root in range(n):
  if seen[root]:continue
  seen[root]=1;stack=[(root,0)]
  while stack:
   x,i=stack[-1]
   if i<len(g[x]):
    y=g[x][i];stack[-1]=(x,i+1)
    if not seen[y]:seen[y]=1;stack.append((y,0))
   else:order.append(x);stack.pop()
 comp=[-1]*n;count=0
 for root in reversed(order):
  if comp[root]>=0:continue
  comp[root]=count;stack=[root]
  while stack:
   x=stack.pop()
   for y in rev[x]:
    if comp[y]<0:comp[y]=count;stack.append(y)
  count+=1
 incoming=[0]*count;outgoing=[0]*count
 for a,b in edges:
  if comp[a]!=comp[b]:outgoing[comp[a]]=1;incoming[comp[b]]=1
 out.append(str(0 if count==1 else max(incoming.count(0),outgoing.count(0))))
print('\\n'.join(out))
''','Condense strongly connected components; minimum edges to strongly connect a nontrivial DAG is max(source count,sink count).'),
84:('''import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);dp={}
 for _ in range(n):
  x=next(it);nxt=dp.copy();nxt[x]=nxt.get(x,0)+1
  for g,count in dp.items():
   d=math.gcd(g,x);nxt[d]=nxt.get(d,0)+count
  dp=nxt
 out.append(str(dp.get(1,0)))
print('\\n'.join(out))
''','Subtraction preserves the GCD; count nonempty subsequences by their GCD without enumerating subsets.'),
86:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);sums=[[0]*(4*n),[0]*(4*n)];lazy=bytearray(4*n)
def swap(x):sums[0][x],sums[1][x]=sums[1][x],sums[0][x];lazy[x]^=1
def push(x):
 if lazy[x]:swap(x*2);swap(x*2+1);lazy[x]=0
def operate(x,l,r,ql,qr,typ,arr=0,value=0):
 if ql<=l and r<=qr:
  if typ==0:return sums[arr][x]
  if typ==2:swap(x);return 0
  sums[arr][x]=value;return 0
 push(x);mid=(l+r)//2;answer=0
 if ql<=mid:answer+=operate(x*2,l,mid,ql,qr,typ,arr,value)
 if qr>mid:answer+=operate(x*2+1,mid+1,r,ql,qr,typ,arr,value)
 if typ:
  for a in (0,1):sums[a][x]=sums[a][x*2]+sums[a][x*2+1]
 return answer
out=[]
for _ in range(m):
 typ=next(it)
 if typ==2:operate(1,0,n-1,next(it),next(it),2)
 else:
  arr=next(it);l=next(it);r=next(it)
  if typ==0:out.append(str(operate(1,0,n-1,l,r,0,arr)))
  else:operate(1,0,n-1,l,l,1,arr,r)
print('\\n'.join(out))
''','One lazy segment tree stores both array sums; range swaps exchange the two aggregates and toggle a lazy bit.'),
87:('''import sys,math
n,m=map(int,sys.stdin.buffer.read().split());print(math.comb(n+2*m-1,2*m)%1000000007)
''','Concatenate a and reversed b to get one nondecreasing sequence of length 2m; stars and bars.'),
88:('''import sys
x=int(sys.stdin.buffer.read());black=[i for i in range(16) if x>>(15-i)&1];targets=list(range(8,16));dp=[1000]*256;dp[0]=0
for mask in range(255):
 i=mask.bit_count();source=black[i]
 for j,target in enumerate(targets):
  if not(mask>>j&1):
   nxt=mask|1<<j;cost=dp[mask]+abs(source//4-target//4)+abs(source%4-target%4)
   if cost<dp[nxt]:dp[nxt]=cost
print(dp[255])
''','Minimum unit grid transport equals a minimum Manhattan matching from the eight black cells to the bottom eight target cells.'),
90:('''import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for case in range(1,t+1):
 n=next(it);m=next(it);br=next(it)-1;bc=next(it)-1;a=[[next(it) for _ in range(m)] for _ in range(n)];dist=[[1000000]*m for _ in range(n)];dist[br][bc]=0;heap=[(0,br,bc)];answer=None
 while heap:
  cost,r,c=heapq.heappop(heap)
  if cost!=dist[r][c]:continue
  if r in (0,n-1) or c in (0,m-1):answer=cost;break
  for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if 0<=rr<n and 0<=cc<m and a[rr][cc]>=a[r][c]:
    candidate=max(cost,a[rr][cc]-a[r][c])
    if candidate<dist[rr][cc]:dist[rr][cc]=candidate;heapq.heappush(heap,(candidate,rr,cc))
 out.append(f'{case}. '+('IMPOSSIBLE' if answer is None else str(answer)))
print('\\n'.join(out))
''','Reverse traversal from the boss uses only nondecreasing heights; bottleneck Dijkstra reaches the safest boundary.'),
91:('''import sys
n=int(sys.stdin.buffer.read());print((n-1)*(n-1)//4)
''','Reverse two balanced contiguous blocks around the circle; minimal adjacent swaps are floor((n-1)^2/4).'),
93:('''import sys
from collections import deque
n,m,k=map(int,sys.stdin.buffer.readline().split());height=n+2*k;width=m+2*k;dist=[[-1]*width for _ in range(height)];queue=deque();water=0
for i in range(n):
 row=sys.stdin.buffer.readline().strip()
 for j,ch in enumerate(row):
  if ch==35:dist[i+k][j+k]=0;queue.append((i+k,j+k));water+=1
count=0
while queue:
 r,c=queue.popleft();count+=1
 if dist[r][c]==k:continue
 for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
  if 0<=rr<height and 0<=cc<width and dist[rr][cc]<0:dist[rr][cc]=dist[r][c]+1;queue.append((rr,cc))
print(count-water)
''','Multi-source Manhattan-distance BFS on the photograph padded by k on every side; subtract water cells.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2));shutil.copytree(p,D/'upload/tasks'/rows[i]['id']/p.name,dirs_exist_ok=True)
# Explicit new candidate retains the previous failed implementation.
i=58;old=D/'tasks'/rows[i]['id']/'candidate_01';code=(old/'solution.py').read_text().replace('ans[j]=count(low)-count(high+1)','ans[j]=count(low)-count(high+1) if low<=high else 0');p=old.parent/'candidate_02';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);author=json.loads((old/'AUTHOR.json').read_text());author.update(solution_sha256=hashlib.sha256(code.encode()).hexdigest(),reasoning=author['reasoning']+' Empty length intervals must count zero; statement does not promise a<=b. Independently reproduced with brute-force enumeration.');(p/'AUTHOR.json').write_text(json.dumps(author,indent=2));shutil.copytree(p,D/'upload/tasks'/rows[i]['id']/p.name,dirs_exist_ok=True)
