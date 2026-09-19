from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
35:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];p=[0]
for x in a:p.append(p[-1]+x)
mod=1000000007;prev=[0]*(n+1);prev[0]=1;answer=0
for k in range(1,n+1):
 sums=[0]*k;cur=[0]*(n+1)
 for i in range(k,n+1):
  r=p[i-1]%k;sums[r]=(sums[r]+prev[i-1])%mod;cur[i]=sums[p[i]%k]
 answer=(answer+cur[n])%mod;prev=cur
print(answer)
''','Partition DP by segment count and prefix-sum residue; quadratic time, linear working memory.'),
37:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];c=v[1:n+1];g=[[] for _ in range(n)]
for i in range(n+1,len(v),2):
 a,b=v[i]-1,v[i+1]-1;g[a].append(b);g[b].append(a)
par=[-1]*n;order=[0]
for x in order:
 for y in g[x]:
  if y!=par[x]:par[y]=x;order.append(y)
d=[None]*n;freq=[0]*n;ans=[0]*n
for x in reversed(order):
 children=[y for y in g[x] if par[y]==x];heavy=max(children,key=lambda y:len(d[y])) if children else -1
 if heavy<0:base={};best=0;total=0
 else:base=d[heavy];best=freq[heavy];total=ans[heavy];d[heavy]=None
 for y in children:
  if y==heavy:continue
  for col,num in d[y].items():
   count=base.get(col,0)+num;base[col]=count
   if count>best:best=count;total=col
   elif count==best:total+=col
  d[y]=None
 col=c[x];count=base.get(col,0)+1;base[col]=count
 if count>best:best=count;total=col
 elif count==best:total+=col
 d[x]=base;freq[x]=best;ans[x]=total
print(*ans)
''','Small-to-large color frequency maps; keep maximum frequency and sum of tied colors.'),
39:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
while True:
 try:n=next(it);q=next(it)
 except StopIteration:break
 if n==q==0:break
 w=[next(it) for _ in range(n)];dp=[0]*(n+1);dp[0]=1
 for i,x in enumerate(w,1):
  for k in range(i,0,-1):dp[k]|=dp[k-1]<<x
 total=sum(w)
 for _ in range(q):
  x=next(it);counts=[str(k) for k in range(n+1) if 0<=x<=total and (dp[k]>>x)&1]
  out.append(' '.join(counts) if counts else "That's impossible!")
print('\\n'.join(out))
''','0/1 subset sum bitsets indexed by number of chosen pieces, including zero-piece weight0.'),
40:('''import sys
from fractions import Fraction
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];p=list(zip(v[1::2],v[2::2]));area=moment=0
for i in range(n):
 x,y=p[i];u,w=p[(i+1)%n];cross=x*w-y*u;area+=cross;moment+=(x+u)*cross
if area<0:area=-area;moment=-moment
support=[x for x,y in p if y==0];L=min(support);R=max(support);x=p[0][0];lo=Fraction(0);hi=None;valid=True
for coef,rhs in [(6*(x-L),3*L*area-moment),(6*(R-x),moment-3*R*area)]:
 if coef>0:lo=max(lo,Fraction(rhs,coef))
 elif coef<0:
  bound=Fraction(rhs,coef);hi=bound if hi is None else min(hi,bound)
 elif rhs>0:valid=False
if not valid or (hi is not None and hi<lo):print('unstable')
else:print(f'{lo.numerator//lo.denominator} .. '+('inf' if hi is None else str(-(-hi.numerator//hi.denominator))))
''','Exact rational centroid moment and support interval inequalities; no floating rounding ambiguity.'),
42:('''import sys
out=[]
for n in map(int,sys.stdin.buffer.read().split()):
 if n==0:break
 ans=0;l=1
 while l<=n:
  q=n//l;r=n//q;ans+=q*(l+r)*(r-l+1)//2;l=r+1
 out.append(str(ans-1))
print('\\n'.join(out))
''','Maximum LCM-constrained set consists of all divisors; quotient-grouped summatory sigma minus sigma(1).'),
43:('''import sys
terms=sys.stdin.read().strip().split('|');pos={x for x in terms if not x.startswith('~')};neg={x[1:] for x in terms if x.startswith('~')};print((1<<len(pos|neg))-(0 if pos&neg else 1))
''','Disjunction false under exactly one assignment unless opposite literals make it tautological.'),
44:('''import sys
a=list(map(int,sys.stdin.buffer.read().split()))[1:];dp=[0]*4;pat=[1,2,1,2]
for x in a:
 best=0;nd=[]
 for j in range(4):best=max(best,dp[j]);nd.append(best+(x==pat[j]))
 dp=nd
print(max(dp))
''','One reversal yields optimal subsequence pattern 1*2*1*2* before reversal; four-stage DP.'),
46:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);k=next(it);a=[[next(it) for _ in range(m)] for _ in range(n)]
if n>m:a=list(map(list,zip(*a)));n,m=m,n
ans=0
for top in range(n):
 sums=[0]*m
 for bottom in range(top,n):
  seen={0:1};p=0;row=a[bottom]
  for j in range(m):
   sums[j]+=row[j];p=(p+sums[j])%k;cnt=seen.get(p,0);ans+=cnt;seen[p]=cnt+1
print(ans)
''','Enumerate row bands on smaller dimension and count equal prefix residues. Visible statement omits numeric dimension bounds; complexity explicitly O(min(n,m)^2 max(n,m)).'),
47:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=sorted([(v[i+1],i+1) for i in range(n)],reverse=True);q=v[n+1];queries=[]
for j in range(q):
 l,r,k=v[n+2+3*j:n+5+3*j];queries.append((k,l,r,j))
queries.sort(reverse=True);bit=[0]*(n+1);ans=[0]*q;pos=0
def pref(x):
 s=0
 while x:s+=bit[x];x-=x&-x
 return s
for k,l,r,j in queries:
 while pos<n and a[pos][0]>k:
  x=a[pos][1]
  while x<=n:bit[x]+=1;x+=x&-x
  pos+=1
 ans[j]=pref(r)-pref(l-1)
print('\\n'.join(map(str,ans)))
''','Offline descending thresholds with Fenwick active positions; strict greater-than comparison.'),
48:('''import sys
from array import array
n=int(sys.stdin.buffer.read());lp=array('i',[0])*(n+1)
for p in range(2,n+1):
 if lp[p]==0:
  for j in range(p,n+1,p):lp[j]=p
lo=n-lp[n]+1;ans=n
for x in range(lo,n+1):
 if lp[x]!=x:ans=min(ans,x-lp[x]+1)
print(ans)
''','Largest prime factors give widest predecessor intervals; scan allowable intermediate composite values.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2))
