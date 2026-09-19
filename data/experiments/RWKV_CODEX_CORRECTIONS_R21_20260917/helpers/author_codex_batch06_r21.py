from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
65:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];w=v[n+1:];left=[w[i] for i in range(n) if a[i]];right=[w[i] for i in range(n) if not a[i]];print(min(left)+min(right) if left and right else 0)
''','Group each handedness contiguously: exactly one conflicting interface is sufficient and unavoidable; choose the cheapest member of each hand.'),
67:('''import sys,math,bisect
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];limit=math.isqrt(max(a));g=bytearray(limit+1);freq=[0]*64;left=1;right=0
for x in range(2,limit+1):
 hi=math.isqrt(x);lo=math.isqrt(hi)
 if lo**4<x:lo+=1
 while right<hi:right+=1;freq[g[right]]+=1
 while left<lo:freq[g[left]]-=1;left+=1
 mex=0
 while freq[mex]:mex+=1
 g[x]=mex
positions=[[] for _ in range(max(g)+1)]
for x,value in enumerate(g):positions[value].append(x)
answer=0
for x in a:
 if x<=limit:value=g[x]
 else:
  hi=math.isqrt(x);lo=math.isqrt(hi)
  if lo**4<x:lo+=1
  value=0
  while value<len(positions):
   p=positions[value];i=bisect.bisect_left(p,lo)
   if i==len(p) or p[i]>hi:break
   value+=1
 answer^=value
print('Furlo' if answer else 'Rublo')
''','Exact integer-root move bounds; sliding mex precomputation to sqrt(max pile), then range-presence queries for large piles.'),
70:('''import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=sorted(v[1:n+1]);p=[0]
for x in a:p.append(p[-1]+x)
out=[]
for i in range(v[n+1]):
 l,r=v[n+2+2*i:n+4+2*i];out.append(str(p[bisect.bisect_right(a,r)]-p[bisect.bisect_left(a,l)]) if l<=r else '0')
print('\\n'.join(out))
''','Sorted prices and prefix sums with inclusive binary-search endpoints.'),
71:('''import sys,math
n=int(sys.stdin.buffer.read());size=(n+1)//2;sieve=bytearray(b'\\1')*size
if size:sieve[0]=0
for p in range(3,math.isqrt(n)+1,2):
 if sieve[p//2]:
  start=p*p//2;sieve[start::p]=b'\\0'*((size-1-start)//p+1)
print(sum(sieve)+(n>=2))
''','Odd-only Eratosthenes with bytearray slice marking; at most 50MB main sieve at N=1e8.'),
72:('''import sys
it=iter(sys.stdin.buffer.read().split());out=[]
while True:
 try:n=int(next(it))
 except StopIteration:break
 if not n:break
 p=[(float(next(it)),float(next(it))) for _ in range(n)];points=[(x,y-d) for x,y in p for d in (0,1)];best=p[0][0];through=False
 for i,(x,y) in enumerate(points):
  if through:break
  for u,v in points[i+1:]:
   if abs(u-x)<1e-12:continue
   slope=(v-y)/(u-x);intercept=y-slope*x;first=slope*p[0][0]+intercept
   if first<p[0][1]-1-1e-8 or first>p[0][1]+1e-8:continue
   reached=p[-1][0]
   for j in range(1,n):
    xx,upper=p[j];ray=slope*xx+intercept
    if ray<upper-1-1e-8 or ray>upper+1e-8:
     shift=0 if ray>upper else -1;px,py=p[j-1];before=slope*px+intercept-(py+shift);after=ray-(upper+shift);reached=px+(xx-px)*(-before)/(after-before);break
   else:through=True
   best=max(best,reached)
   if through:break
 out.append('Through all the pipe.' if through else f'{best:.2f}')
print('\\n'.join(out))
''','Enumerate lines through wall vertices, validate entrance and locate the first segment collision by linear interpolation.'),
73:('''import sys
from functools import lru_cache
l,r=map(int,sys.stdin.buffer.read().split())
def count(bound):
 if bound<10**10:return 0
 digits=list(map(int,str(bound)))
 @lru_cache(None)
 def visit(pos,last,run,found,mask,tight):
  if pos==11:return int(found)
  total=0;upper=digits[pos] if tight else 9
  for d in range(1 if pos==0 else 0,upper+1):
   m=mask|(1 if d==4 else 2 if d==8 else 0)
   if m==3:continue
   length=min(3,run+1) if d==last else 1;total+=visit(pos+1,d,length,found or length==3,m,tight and d==upper)
  return total
 return visit(0,-1,0,False,0,True)
print(count(r)-count(l-1))
''','Digit DP tracks previous digit, run length, triple occurrence, and exclusion of simultaneous 4 and 8.'),
74:('''import sys
s=sys.stdin.buffer.readline().strip();n=len(s);v=list(map(int,sys.stdin.buffer.read().split()));q=v[0];queries=sorted((v[2+2*i],v[1+2*i],i) for i in range(q));bit=[0]*(n+1);stack=[];answer=[0]*q;pos=0;total=0
for r,l,i in queries:
 while pos<r:
  if s[pos]==40:stack.append(pos+1)
  elif stack:
   x=stack.pop();total+=1
   while x<=n:bit[x]+=1;x+=x&-x
  pos+=1
 x=l-1;before=0
 while x:before+=bit[x];x-=x&-x
 answer[i]=2*(total-before)
print('\\n'.join(map(str,answer)))
''','Offline right endpoints; globally matched brackets fully inside each interval form its maximal subsequence. Fenwick counts matched opening positions.'),
78:('''import sys,re,math
from functools import lru_cache
lines=sys.stdin.read().splitlines();loops=[]
for line in lines[1:]:
 match=re.search(r'for ([a-z]) in range\\(([^,]+),\\s*([^\\)]+)\\)',line)
 if match:loops.append(tuple(x.strip() for x in match.groups()))
n=len(loops);names={x[0]:i for i,x in enumerate(loops)};reach=[1<<i for i in range(n)]
for i,(_,lo,hi) in enumerate(loops):
 if lo in names:reach[names[lo]]|=1<<i
 if hi in names:reach[i]|=1<<names[hi]
for k in range(n):
 for i in range(n):
  if reach[i]>>k&1:reach[i]|=reach[k]
components=[];owner=[-1]*n
for i in range(n):
 if owner[i]<0:
  group=[j for j in range(n) if reach[i]>>j&1 and reach[j]>>i&1]
  for j in group:owner[j]=len(components)
  components.append(group)
k=len(components);pred=[0]*k
for i in range(n):
 for j in range(n):
  if owner[i]!=owner[j] and reach[i]>>j&1:pred[owner[j]]|=1<<owner[i]
full=(1<<k)-1
@lru_cache(None)
def ways(done):
 if done==full:return 1
 remaining=full^done;available=0;bits=remaining
 while bits:
  b=bits&-bits;bits-=b;i=b.bit_length()-1
  if pred[i]&remaining==0:available|=b
 if available==remaining:return math.factorial(remaining.bit_count())
 total=0
 while available:
  b=available&-available;available-=b;total+=ways(done|b)
 return total
p=ways(0);q=math.factorial(k);g=math.gcd(p,q);print(k,f'{p//g}/{q//g}')
''','Loop bounds define a weak partial order; SCCs force equality. Leading coefficient is the number of linear extensions divided by factorial of free components.'),
79:('''import sys
f=sys.stdin.buffer;n,m=map(int,f.readline().split());size=1<<n;skills=[0]+[int(f.readline()) for _ in range(size)];tree=[0]*size+list(range(1,size+1))
for x in range(size-1,0,-1):
 l=tree[x*2];r=tree[x*2+1];tree[x]=l if skills[l]>skills[r] else r
out=[]
for _ in range(m):
 p=f.readline().split()
 if p[0]==b'W':out.append(str(tree[1]))
 elif p[0]==b'R':
  i=int(p[1]);skills[i]=int(p[2]);x=(size+i-1)//2
  while x:
   l=tree[x*2];r=tree[x*2+1];winner=l if skills[l]>skills[r] else r
   tree[x]=winner;x//=2
 else:
  i=int(p[1]);x=(size+i-1)//2;wins=0
  while x and tree[x]==i:wins+=1;x//=2
  out.append(str(wins))
print('\\n'.join(out))
''','Tournament segment tree stores winning positions; update one root path and count consecutive won ancestors.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2));shutil.copytree(p,D/'upload/tasks'/rows[i]['id']/p.name,dirs_exist_ok=True)
