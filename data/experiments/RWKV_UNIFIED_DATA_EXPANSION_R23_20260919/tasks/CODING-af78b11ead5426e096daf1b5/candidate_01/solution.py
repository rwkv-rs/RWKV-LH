import sys
from collections import deque
v=sys.stdin.read().split();n=int(v[0]);k=int(v[1]);s=v[2];distance=[-1]*n;color=list(s);q=deque()
for i in range(n):
 if s[i]==s[(i-1)%n] or s[i]==s[(i+1)%n]:distance[i]=0;q.append(i)
while q:
 i=q.popleft()
 for j in ((i-1)%n,(i+1)%n):
  if distance[j]<0:distance[j]=distance[i]+1;color[j]=color[i];q.append(j)
print(''.join(color[i] if 0<=distance[i]<=k else ('B' if s[i]=='W' else 'W') if k%2 else s[i] for i in range(n)))
