from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
96:('''import sys
lines=sys.stdin.read().split();out=[]
for s in lines[1:]:
 chars={c:i for i,c in enumerate(sorted(set(s)))};k=len(chars);singles=0;pairs=[0]*k;triples=[0]*k
 for ch in s:
  c=chars[ch];mask=0
  for first in range(k):mask|=pairs[first]<<(first*k)
  triples[c]|=mask
  for first in range(k):
   if singles>>first&1:pairs[first]|=1<<c
  singles|=1<<c
 out.append(str(sum(x.bit_count() for x in triples)))
print('\\n'.join(out))
''','Bitsets accumulate distinct ordered pairs and triples while scanning; updates occur longest-first to avoid reusing a position.'),
97:('''import sys
from array import array
a,b=sys.stdin.read().split();trans=[{}];link=[-1];length=[0];last=0
for ch in b:
 cur=len(trans);trans.append({});length.append(length[last]+1);link.append(0);p=last
 while p>=0 and ch not in trans[p]:trans[p][ch]=cur;p=link[p]
 if p>=0:
  q=trans[p][ch]
  if length[p]+1==length[q]:link[cur]=q
  else:
   clone=len(trans);trans.append(trans[q].copy());length.append(length[p]+1);link.append(link[q])
   while p>=0 and trans[p].get(ch)==q:trans[p][ch]=clone;p=link[p]
   link[q]=link[cur]=clone
 last=cur
inf=len(a)+1;answer1=inf;state=matched=0
for i,ch in enumerate(a):
 while state and ch not in trans[state]:state=link[state];matched=min(matched,length[state])
 if ch in trans[state]:state=trans[state][ch];matched+=1
 else:matched=0
 if matched<i+1:answer1=min(answer1,matched+1)
m=len(b);nxt=[None]*(m+1);nxt[m]=array('i',[-1])*26
for i in range(m-1,-1,-1):nxt[i]=nxt[i+1][:];nxt[i][ord(b[i])-97]=i+1
answer2=inf;codes=[ord(c)-97 for c in a]
for i in range(len(a)):
 pos=0
 for j in range(i,min(len(a),i+answer2)):
  pos=nxt[pos][codes[j]]
  if pos<0:answer2=min(answer2,j-i+1);break
def shortest(transitions,states):
 dp=[inf]*states;dp[0]=0;answer=inf
 for ch in a:
  updated=dp[:]
  for state,cost in enumerate(dp):
   if cost+1>=answer:continue
   to=transitions(state,ch)
   if to<0:answer=cost+1
   elif cost+1<updated[to]:updated[to]=cost+1
  dp=updated
 return answer
answers=[answer1,answer2,shortest(lambda s,c:trans[s].get(c,-1),len(trans)),shortest(lambda s,c:nxt[s][ord(c)-97],m+1)]
print('\\n'.join(str(x if x<inf else -1) for x in answers))
''','Suffix automaton handles substring membership; next-occurrence automaton handles subsequences. Contiguous scans and shortest selected-path DP cover the four combinations.'),
99:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,q=v[:2];books=sorted(v[2:2+n]);out=[]
for i in range(q):
 length,code=v[2+n+2*i:4+n+2*i];mod=10**length;out.append(str(next((x for x in books if x%mod==code),-1)))
print('\\n'.join(out))
''','Sorted books and exact decimal suffix comparison return the smallest matching code.'),
100:('''import sys,math
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);k=[next(it) for _ in range(n)];edges=[];period=1
for _ in range(n):
 m=next(it);period=math.lcm(period,m);edges.append([next(it)-1 for _ in range(m)])
answer=array('h',[0])*(n*period);out=[]
for _ in range(next(it)):
 vertex=next(it)-1;c=next(it)%period;state=vertex*period+c;path=[]
 while answer[state]==0:
  answer[state]=-1;path.append(state);vertex,c=divmod(state,period);c=(c+k[vertex])%period;state=edges[vertex][c%len(edges[vertex])]*period+c
 if answer[state]>0:result=answer[state]
 else:
  begin=path.index(state);result=len({s//period for s in path[begin:]})
 for s in path:answer[s]=result
 out.append(str(result))
print('\\n'.join(out))
''','Reduce accumulated counter modulo lcm(outdegrees); functional-graph cycles determine infinitely visited distinct original vertices.'),
103:('''import sys
words=[];case=0;out=[]
for word in sys.stdin.read().split():
 if word=='9':
  case+=1;words.sort();bad=any(words[i+1].startswith(words[i]) for i in range(len(words)-1));out.append(f'Set {case} is '+('not ' if bad else '')+'immediately decodable');words=[]
 else:words.append(word)
print('\\n'.join(out))
''','A sorted adjacent prefix test detects any ambiguous code pair, including duplicate strings.'),
104:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];limit=max(a);weighted=[0]*(limit+1)
for x in a:weighted[x]+=x
exact=[0]*(limit+1);answer=0
for d in range(limit,0,-1):
 total=sum(weighted[d::d]);value=total*total-sum(exact[2*d::d]);exact[d]=value;answer+=value//d
print(answer)
''','Descending divisor inversion isolates sums of products for exact GCD d; divide by d to obtain ordered LCM contributions.'),
105:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);p=next(it);a=[next(it) for _ in range(n)];b=[next(it) for _ in range(n)];remaining=n-1;answer=p
 for cost,capacity in sorted(zip(b,a)):
  if cost>=p:break
  count=min(remaining,capacity);answer+=count*cost;remaining-=count
  if not remaining:break
 answer+=remaining*p;out.append(str(answer))
print('\\n'.join(out))
''','One direct notification seeds the cheapest broadcaster; consume cheapest available forwarding capacities before direct-price slots.'),
106:('''import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);qwq=next(it);a=[next(it) for _ in range(n)];depth=(n-1).bit_length();scale=1<<depth;weights=[0]*n;stack=[(0,n-1,0)]
while stack:
 l,r,d=stack.pop()
 if l==r:weights[l]=2*scale-(scale>>d)
 else:mid=(l+r)//2;stack.append((mid+1,r,d+1));stack.append((l,mid,d+1))
prefix=[0];total=0
for x,w in zip(a,weights):prefix.append(prefix[-1]+w);total+=x*w
out=[]
for _ in range(m):
 l=next(it);r=next(it);x=next(it);total+=x*(prefix[r]-prefix[l-1]);out.append(str(total*qwq//scale))
print('\\n'.join(out))
''','Linearity of expectation gives leaf coefficient sum of ancestor visit probabilities; precompute weighted prefix sums, then each range addition is O(1).'),
107:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));mod=1000000007;out=[]
for n,l in zip(v[::2],v[1::2]):
 if n==l==0:break
 out.append(str(l%mod if n==1 else (pow(n,l+1,mod)-n)*pow(n-1,mod-2,mod)%mod))
print('\\n'.join(out))
''','Finite geometric sum of N^length for lengths 1..L, with the N=1 boundary handled directly.'),
108:('''import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m,p,k=v[:4];template=[v[4+i*p:4+(i+1)*p] for i in range(3)];mask=(1<<m)-1;modmask=(1<<32)-1
horizontal=[j-k for j in range(p) if j!=k and template[1][j]];down=[j-k for j in range(p) if template[2][j]];up=[j-k for j in range(p) if template[0][j]]
def shifted(row,offset):return (row<<offset)&mask if offset>=0 else row>>(-offset)
valid=[row for row in range(1<<m) if all(not(row&shifted(row,d)) for d in horizontal)];size=len(valid);matrix=[[0]*size for _ in range(size)]
for i,a in enumerate(valid):
 for j,b in enumerate(valid):
  if all(not(b&shifted(a,d)) for d in down) and all(not(a&shifted(b,d)) for d in up):matrix[i][j]=1
vector=[1]*size
def multiply(a,b):
 result=[[0]*size for _ in range(size)]
 for i,row in enumerate(a):
  output=result[i]
  for k,value in enumerate(row):
   if value:
    other=b[k]
    for j in range(size):output[j]+=value*other[j]
  for j in range(size):output[j]&=modmask
 return result
power=n-1
while power:
 if power&1:vector=[sum(vector[i]*matrix[i][j] for i in range(size))&modmask for j in range(size)]
 power>>=1
 if power:matrix=multiply(matrix,matrix)
print(sum(vector)&modmask)
''','Enumerate legal row masks and mutual directed attacks between adjacent rows; transfer matrix exponentiation modulo 2^32.'),
109:('''import sys
v=sys.stdin.read().split();words=[]
for word in v[1:]:
 mask=0
 for ch in word:mask|=1<<(ord(ch)-97)
 words.append(mask)
words.sort(key=int.bit_count,reverse=True);n=len(words);suffix=[0]*(n+1)
for i in range(n-1,-1,-1):suffix[i]=suffix[i+1]|words[i]
full=(1<<26)-1
def count(i,have):
 if have==full:return 1<<(n-i)
 if i==n or have|suffix[i]!=full:return 0
 return count(i+1,have|words[i])+count(i+1,have)
print(count(0,0))
''','Enumerate subsets with suffix-union impossibility pruning and immediate counting when the alphabet is already covered.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2));shutil.copytree(p,D/'upload/tasks'/rows[i]['id']/p.name,dirs_exist_ok=True)
