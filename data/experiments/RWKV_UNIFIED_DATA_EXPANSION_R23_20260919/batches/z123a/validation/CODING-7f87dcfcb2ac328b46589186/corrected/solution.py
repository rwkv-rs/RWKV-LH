import sys
from array import array
v=sys.stdin.buffer.read().split();n=int(v[0]);s=v[1];m=int(v[2]);t=v[3];limit=int(v[4])
if t in s:print('YES');raise SystemExit
if limit==1:print('NO');raise SystemExit
# Failure of ordinary subsequence containment is an immediate impossibility.
j=0
for c in s:
 if j<m and c==t[j]:j+=1
if j<m:print('NO');raise SystemExit
text=s+b'\0'+t;length=len(text);alphabet={c:i for i,c in enumerate(sorted(set(text)))};rank=[alphabet[c] for c in text];sa=list(range(length));step=1
while True:
 keys=[rank[i]*(length+1)+(rank[i+step]+1 if i+step<length else 0) for i in range(length)];sa.sort(key=keys.__getitem__);new=[0]*length;value=0
 for i in range(1,length):
  if keys[sa[i]]!=keys[sa[i-1]]:value+=1
  new[sa[i]]=value
 rank=new
 if value==length-1:break
 step*=2
lcp=array('I',[0])*length;matched=0
for i in range(length):
 r=rank[i]
 if r==0:matched=0;continue
 j=sa[r-1]
 while i+matched<length and j+matched<length and text[i+matched]==text[j+matched]:matched+=1
 lcp[r]=matched
 if matched:matched-=1
levels=[lcp];span=1
while 2*span<length:
 old=levels[-1];levels.append(array('I',(min(old[i],old[i+span]) for i in range(len(old)-span))));span*=2
logs=[0]*(length+1)
for i in range(2,length+1):logs[i]=logs[i//2]+1
previous=[0]*(n+1)
for pieces in range(limit):
 current=[0]*(n+1);best=0
 for i in range(n):
  if current[i]>best:best=current[i]
  current[i]=best;j=previous[i]
  if s[i]!=t[j]:continue
  a=rank[i];b=rank[n+1+j]
  if a>b:a,b=b,a
  a+=1;width=b-a+1;k=logs[width];level=levels[k];take=min(level[a],level[b-(1<<k)+1]);reach=j+take
  if reach>=m:print('YES');raise SystemExit
  end=i+take
  if current[end]<reach:current[end]=reach
 current[n]=max(current[n],best);previous=current
print('NO')
