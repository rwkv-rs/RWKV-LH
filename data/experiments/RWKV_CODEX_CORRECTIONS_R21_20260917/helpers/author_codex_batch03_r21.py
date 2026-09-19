from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
22:('''import sys
s,k=sys.stdin.buffer.read().split();k=int(k);mod=1000000007;dp=[0]*(k+1);mask=0
for i,c in enumerate(s):
 d=c-48 if c<=57 else c-55;nd=[0]*(k+1)
 for j in range(1,k+1):nd[j]=(dp[j]*j+dp[j-1]*(17-j))%mod
 if i:nd[1]=(nd[1]+15)%mod
 for v in range(0 if i else 1,d):
  count=(mask|(1<<v)).bit_count()
  if count<=k:nd[count]=(nd[count]+1)%mod
 mask|=1<<d;dp=nd
print((dp[k]+(mask.bit_count()==k))%mod)
''','Digit DP by distinct-count for smaller prefixes; exact prefix uses bitmask; leading zeros excluded.'),
23:('''import sys
h,w=map(int,sys.stdin.buffer.read().split());P=998244353;size=1<<h;M=[[0]*size for _ in range(size)]
for incoming in range(size):
 def fill(i,out):
  if i==h:M[incoming][out]+=1;return
  if incoming>>i&1:fill(i+1,out);return
  fill(i+1,out);fill(i+1,out|(1<<i))
  if i+1<h and not(incoming>>(i+1)&1):fill(i+2,out)
 fill(0,0)
def mul(a,b):
 cols=list(zip(*b));return [[sum(x*y for x,y in zip(row,col))%P for col in cols] for row in a]
v=[[1]+[0]*(size-1)]
while w:
 if w&1:v=mul(v,M)
 w>>=1
 if w:M=mul(M,M)
print(v[0][0])
''','Column occupancy transfer, monomer/vertical/horizontal placements; matrix power handles width up to 1e12.'),
29:('''import sys
out=[]
for token in sys.stdin.buffer.read().split():
 if token==b'*':break
 s=token.decode()
 if s.isdigit():
  number=int(s);x=number;letters=[]
  while x:
   x,r=divmod(x-1,26);letters.append(chr(97+r))
  word=''.join(reversed(letters))
 else:
  word=s;number=0
  for c in word:number=number*26+ord(c)-96
 out.append(f'{word:<22}{number:,}')
print('\\n'.join(out))
''','Bijective base26 conversion; number begins in column23; use stated layout despite malformed sample rendering.'),
30:('''import sys
a=list(map(int,sys.stdin.buffer.read().split()));print('\\n'.join('Roy wins!' if n%6==0 else 'October wins!' for n in a[1:1+a[0]]))
''','No prime power divisible by6, and allowed moves1,2,3,4,5 reach nearest lower multiple of6.'),
31:('''import sys
values=list(map(int,sys.stdin.buffer.read().split()));cache={};out=[]
for n,k in zip(values[::2],values[1::2]):
 if n==0:break
 if n not in cache:
  a=[0]*(2*n+1);seq=[]
  def db(t,p):
   if t>n:
    if n%p==0:seq.extend(a[1:p+1])
   else:
    a[t]=a[t-p];db(t+1,p)
    for j in range(a[t-p]+1,2):a[t]=j;db(t+1,t)
  db(1,1);cache[n]=seq
 seq=cache[n];v=0
 for j in range(n):v=(v<<1)|seq[(k+j)%len(seq)]
 out.append(str(v))
print('\\n'.join(out))
''','FKM Lyndon concatenation yields lexicographically least binary deBruijn cycle; read cyclic n-bit window.'),
32:('''import sys
f=sys.stdin.buffer;n=int(f.readline());traits=[]
for _ in range(n):
 p=f.readline().split();traits.append(set(p[2:2+int(p[1])]))
print(max(len(traits[i]&traits[j]) for i in range(n) for j in range(i))+1)
''','Maximum shared attributes between any pair plus one distinguishing yes.'),
33:('''import sys
k=int(sys.stdin.buffer.read());width=(k-1).bit_length()
for x in range(k):print(''.join('Aa' if x>>j&1 else 'BB' for j in range(width)))
''','Aa and BB have equal Java hash and equal length; concatenate distinct bit choices. Requires semantic output checker, not reference equality.')
}
for i,(code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2))
# Problems whose visible specification cannot yet support a faithful solution.
blocked=[]
for i,reason in [(21,'Two defining good-set closure conditions are missing from the text.'),(26,'No input/output grammar, weights format or example provided.'),(28,'Essential grammar is embedded in external image; must recover source before implementation.'),(27,'Multiple valid transformation sequences; existing exact_rstrip contract cannot establish semantic correctness.'),(33,'Multiple valid collision strings; requires general hash/distinctness/length checker, not exact expected text.')]:
 blocked.append({'id':rows[i]['id'],'ordinal':i,'status':'source_or_acceptance_review_required','reason':reason,'task_sha256':rows[i]['task_sha256']})
(D/'SPECIFICATION_REVIEW.json').write_text(json.dumps(blocked,indent=2))
