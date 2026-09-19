from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
50:('''import sys
from datetime import date,timedelta
v=sys.stdin.read().split();out=[]
for s in v[1:]:
 y,m,d=map(int,s.split(':'));day=date(y,m,d);par=d%2;elapsed=count=0
 while (day.day%2==par)==(elapsed%2==0):
  if elapsed%2==0:count+=1
  elapsed+=1;day+=timedelta(days=1)
 out.append(str(count))
print('\\n'.join(out))
''','Direct Gregorian calendar simulation until the first schedule mismatch; count only actual correct dose days.'),
51:('''import sys,bisect
lines=iter(sys.stdin.read().splitlines());out=[];case=0
for line in lines:
 if not line.strip():continue
 n=int(line)
 if n==0:break
 sections=[];distance=0
 for _ in range(n):
  p=next(lines).split()
  if p[2]=='road':sections.append((0,int(p[3]),[]));distance+=int(p[3])
  else:sections.append((1,int(p[3])*60,[int(x)*60 for x in p[5:]]))
 def arrival(speed):
  t=0.0
  for typ,value,depart in sections:
   if typ==0:t+=value*3600/speed
   else:
    hour=int(t//3600);j=bisect.bisect_left(depart,t-hour*3600-1e-7)
    if j==len(depart):hour+=1;j=0
    t=hour*3600+depart[j]+value
  return t
 end=round(arrival(80));lo=0.0;hi=80.0
 if distance:
  for _ in range(70):
   mid=(lo+hi)/2
   if arrival(mid)<=end+1e-7:hi=mid
   else:lo=mid
 else:hi=0.0
 case+=1;h,rem=divmod(end,3600);m,s=divmod(rem,60);out.append(f'Test Case {case}: {h:02d}:{m:02d}:{s:02d} {hi:.2f}')
print('\\n\\n'.join(out)+'\\n')
''','Monotone earliest-arrival simulation and binary search on maximum road speed; ferry deadlines in seconds.'),
54:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];mean=sum(a)//n;p=0;s=[]
for x in a:p+=x-mean;s.append(p)
s.sort();median=s[n//2];print(sum(abs(x-median) for x in s))
''','Circular flow differs by one constant; median minimizes absolute cumulative excess.'),
55:('''import sys,math
from fractions import Fraction
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);lines=[];pieces=1
 for _ in range(n):
  x,y,u,v=[next(it) for j in range(4)];a=y-v;b=u-x;c=x*v-u*y;g=math.gcd(math.gcd(abs(a),abs(b)),abs(c));a//=g;b//=g;c//=g
  if a<0 or (a==0 and b<0):a=-a;b=-b;c=-c
  line=(a,b,c)
  if line in lines:continue
  points=set()
  for d,e,f in lines:
   det=a*e-b*d
   if det:
    xx=Fraction(b*f-c*e,det);yy=Fraction(c*d-a*f,det)
    if 0<xx<1000 and 0<yy<1000:points.add((xx,yy))
  pieces+=1+len(points);lines.append(line)
 out.append(str(pieces))
print('\\n\\n'.join(out))
''','Each new distinct cut adds one plus distinct strictly interior intersections; exact rationals handle concurrence.'),
56:('''import sys
from collections import deque
n,m,k=map(int,sys.stdin.buffer.readline().split());stride=m+2;grid=bytearray(b'*'*stride)
for _ in range(n):grid.extend(b'*'+sys.stdin.buffer.readline().strip()+b'*')
grid.extend(b'*'*stride);start=grid.index(88);dist=[-1]*len(grid);dist[start]=0;q=deque([start]);steps=[(stride,'D'),(-1,'L'),(1,'R'),(-stride,'U')]
if k%2:print('IMPOSSIBLE');raise SystemExit
while q:
 x=q.popleft()
 for delta,_ in steps:
  y=x+delta
  if grid[y]!=42 and dist[y]<0:dist[y]=dist[x]+1;q.append(y)
x=start;out=[]
for remaining in range(k-1,-1,-1):
 for delta,ch in steps:
  y=x+delta
  if dist[y]>=0 and dist[y]<=remaining:x=y;out.append(ch);break
 else:print('IMPOSSIBLE');raise SystemExit
print(''.join(out))
''','BFS return distances, then lexicographic greedy moves whose remaining budget permits a return; grid parity excludes odd cycles.'),
58:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,q=v[:2];a=v[2:2+n];queries=[]
for i in range(q):
 threshold,low,high=v[2+n+3*i:5+n+3*i];queries.append((threshold,low,high,i))
queries.sort(reverse=True);order=sorted(range(n),key=a.__getitem__,reverse=True);parent=list(range(n));size=[1]*n;active=[False]*n;bc=[0]*(n+1);bs=[0]*(n+1);bq=[0]*(n+1);tc=ts=tq=0
def change(length,delta):
 global tc,ts,tq
 tc+=delta;ts+=delta*length;tq+=delta*length*length;i=length
 while i<=n:bc[i]+=delta;bs[i]+=delta*length;bq[i]+=delta*length*length;i+=i&-i
def root(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
def count(low):
 if low>n:return 0
 low=max(1,low);c=tc;s=ts;sq=tq;i=low-1
 while i:c-=bc[i];s-=bs[i];sq-=bq[i];i-=i&-i
 return (sq+(3-2*low)*s+(low-1)*(low-2)*c)//2
pos=0;ans=[0]*q
for threshold,low,high,j in queries:
 while pos<n and a[order[pos]]>=threshold:
  x=order[pos];pos+=1;active[x]=True;change(1,1)
  for y in (x-1,x+1):
   if 0<=y<n and active[y]:
    r=root(x);s=root(y)
    if r!=s:
     change(size[r],-1);change(size[s],-1)
     if size[r]<size[s]:r,s=s,r
     parent[s]=r;size[r]+=size[s];change(size[r],1)
 ans[j]=count(low)-count(high+1)
print('\\n'.join(map(str,ans)))
''','Offline threshold activation and DSU runs; Fenwick zeroth/first/second moments count all allowed subarray lengths.'),
59:('''import sys,math
n,k=map(int,sys.stdin.buffer.read().split());mod=998244353;inv=[0]+[pow(i,mod-2,mod) for i in range(1,n+1)];cache={};answer=0
def visit(left,minimum,lcm,weight,last,count):
 global answer
 if left==0:
  power=cache.get(lcm)
  if power is None:power=pow(lcm,k,mod);cache[lcm]=power
  answer=(answer+weight*power)%mod;return
 for length in range(minimum,left+1):
  if left!=length and left-length<length:continue
  multiplicity=count+1 if length==last else 1
  visit(left-length,length,lcm//math.gcd(lcm,length)*length,weight*inv[length]%mod*inv[multiplicity]%mod,length,multiplicity)
visit(n,1,1,1,0,0);print(answer*math.factorial(n)%mod)
''','Enumerate cycle-length partitions, weight n!/product(length^multiplicity * multiplicity!), and score by cycle-length LCM.'),
64:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 s=next(it);n=next(it);last={};diff=[0]*(s+1)
 for q in range(n):
  song=next(it);p=last.get(song);last[song]=q
  if p is not None and q-p<s:
   left=(q+1)%s;right=p%s
   if left<=right:diff[left]+=1;diff[right+1]-=1
   else:diff[left]+=1;diff[s]-=1;diff[0]+=1;diff[right+1]-=1
 total=answer=0
 for i in range(s):total+=diff[i];answer+=total==0
 out.append(str(answer))
print('\\n'.join(out))
''','Every adjacent equal-song pair requires a shuffle boundary between it; cyclic difference array rejects incompatible boundary phases.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2));shutil.copytree(p,D/'upload/tasks'/rows[i]['id']/p.name,dirs_exist_ok=True)
