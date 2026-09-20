import sys
from collections import deque
v=sys.stdin.buffer.read().split();n,k=int(v[0]),int(v[1]);s=v[2].decode();color=list(s);distance=[-1]*n;q=deque()
for i in range(n):
 if s[i]==s[(i-1)%n] or s[i]==s[(i+1)%n]:distance[i]=0;q.append(i)
while q:
 i=q.popleft()
 for j in ((i-1)%n,(i+1)%n):
  if distance[j]<0:distance[j]=distance[i]+1;color[j]=color[i];q.append(j)
for i in range(n):
 if distance[i]<0 or distance[i]>k:color[i]=s[i] if k%2==0 else ('B' if s[i]=='W' else 'W')
print(''.join(color))
