from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
7:'''import sys
it=iter(sys.stdin.buffer.read().split());t=int(next(it));out=[]
for _ in range(t):
 s=next(it);last=0;best=1
 for i,c in enumerate(s,1):
  if c==82:
   best=max(best,i-last);last=i
 out.append(str(max(best,len(s)+1-last)))
print('\\n'.join(out))
''',
8:'''import sys
a=list(map(int,sys.stdin.buffer.read().split()));print(*a[1:1+a[0]][::-1])
''',
11:'''import sys
a=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(1,len(a),2):
 x,y=a[i:i+2];out.append(f"{max(0,x-y)} {y}")
print('\\n'.join(out))
''',
12:'''import sys
n=int(sys.stdin.buffer.read());s={0}
for _ in range(min(n,12)):
 s={x+d for x in s for d in (1,5,10,50)}
print(len(s)+max(0,n-12)*49)
''',
13:'''import sys
a=list(map(int,sys.stdin.buffer.read().split()));n=a[0];p=[(a[2*i+1]&1,a[2*i+2]&1) for i in range(n)]
pref=[0]*n
for i in range(1,n):
 x,y=p[i-1];u,v=p[i];pref[i]=pref[i-1]^((x*v-y*u)&1)
x,y=p[-1];u,v=p[0]
if pref[-1]^((x*v-y*u)&1):print(0)
else:
 count=[[[0]*2 for _ in range(2)] for _ in range(2)];ans=0
 for j,(x,y) in enumerate(p):
  for u in range(2):
   for v in range(2):ans+=count[u][v][pref[j]^((x*v-y*u)&1)]
  count[x][y][pref[j]]+=1
 print(ans-n)
''',
16:'''import sys
a=list(map(int,sys.stdin.buffer.read().split()));n,k=a[:2];key=[-1]*256;out=[]
for x in a[2:2+n]:
 if key[x]<0:
  lo=max(0,x-k+1);j=x
  while j>=lo and key[j]<0:j-=1
  if j<lo:start=lo
  elif x-key[j]<k:start=key[j]
  else:start=j+1
  for v in range(start,x+1):
   if key[v]<0:key[v]=start
 out.append(str(key[x]))
print(' '.join(out))
''',
17:'''import sys
f=sys.stdin.buffer;n,m=map(int,f.readline().split());a=list(range(1,n+1));rev=False;changed=[]
for line in f:
 p=list(map(int,line.split()))
 if not p:continue
 op=p[0]
 if op in (1,2):
  for j in changed:a[j]=j+1
  changed.clear();rev=op==2
 elif op==4:rev=not rev
 else:
  x,y=p[1]-1,p[2]-1
  if rev:x=n-1-x;y=n-1-y
  a[x],a[y]=a[y],a[x];changed.extend((x,y))
if rev:a.reverse()
print(*a)
''',
18:'''import sys
a=list(map(int,sys.stdin.buffer.read().split()));n=a[0];b=a[1:n+1];need=a[n+1:2*n+1];d=[b[i]-need[i] for i in range(n)];parents=[0]*n;factor=[1]*n
for i in range(1,n):parents[i]=a[2*n+1+2*(i-1)]-1;factor[i]=a[2*n+2+2*(i-1)]
limit=sum(b)
for i in range(n-1,0,-1):
 v=d[i] if d[i]>=0 else d[i]*factor[i]
 if v < -limit:print('NO');break
 d[parents[i]]+=v
else:print('YES' if d[0]>=0 else 'NO')
''',
2:'''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];reach=1;mask=(1<<k)-1;A=B=0
for i in range(n):
 a,b=v[2+2*i:4+2*i];A+=a;B+=b
 lo=max(0,k-b);hi=min(k,a)
 if lo<=hi:
  bits=reach;width=hi-lo+1;span=1
  while span<width:
   step=min(span,width-span)%k
   bits|=((bits<<step)|(bits>>(k-step)))&mask
   span+=min(span,width-span)
  shift=lo%k;reach|=((bits<<shift)|(bits>>(k-shift)))&mask
ans=(A+B)//k
for r in range(k):
 if (reach>>r)&1 and (A-r)%k+(B+r)%k<k:print(ans);break
else:print(ans-1)
'''
}
notes={7:'Largest gap between right-jump positions including endpoints.',8:'Reverse exactly n input values.',11:'Optimal play yields Bob y wins and Alice max(x-y,0); verify small game separately.',12:'Sumset eventually gains 49 per digit; independently verify stabilization.',13:'Even doubled total area necessary; count parity-compatible vertex pairs then exclude n edges.',16:'Greedy smallest compatible color interval; never merge across a conflicting assigned group.',17:'Lazy reversal plus restoration only touched indices on sort; linear total operations.',18:'Bottom-up tree deficits multiplied, surpluses passed 1:1; any deficit beyond total initial supply impossible.',2:'Cyclic bitset for mixed basket red consumption; contiguous allowed shifts per shrub. Max baskets is total floor or one less.'}
for i,code in solutions.items():
 folder=D/'tasks'/rows[i]['id'];p=folder/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':notes[i],'hidden_cases_read':False,'training_admitted':False},indent=2))
print('authored',len(solutions))
