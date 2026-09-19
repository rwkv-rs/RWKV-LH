import sys
from collections import deque
v=sys.stdin.read().split();n=int(v[0]);m=int(v[1]);go=[[-1]*26];fail=[0];bad=[False]
for word in v[2:2+n]:
 p=0
 for c in word:
  k=ord(c)-65
  if go[p][k]<0:go[p][k]=len(go);go.append([-1]*26);fail.append(0);bad.append(False)
  p=go[p][k]
 bad[p]=True
q=deque()
for c in range(26):
 if go[0][c]<0:go[0][c]=0
 else:q.append(go[0][c])
while q:
 p=q.popleft();bad[p]|=bad[fail[p]]
 for c in range(26):
  if go[p][c]<0:go[p][c]=go[fail[p]][c]
  else:fail[go[p][c]]=go[fail[p]][c];q.append(go[p][c])
mod=10007;dp=[0]*len(go);dp[0]=1
for _ in range(m):
 nd=[0]*len(go)
 for p,count in enumerate(dp):
  if count:
   for dest in go[p]:
    if not bad[dest]:nd[dest]=(nd[dest]+count)%mod
 dp=nd
print((pow(26,m,mod)-sum(dp))%mod)
