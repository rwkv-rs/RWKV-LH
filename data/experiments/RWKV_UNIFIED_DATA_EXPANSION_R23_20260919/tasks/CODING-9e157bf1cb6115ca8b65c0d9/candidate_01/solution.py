import sys
from collections import deque
parts=sys.stdin.read().split();words=[];punct=[];ids={}
for s in parts:
 p=s[-1] if s[-1] in ',.' else '';w=s[:-1] if p else s
 if w not in ids:ids[w]=len(ids)
 words.append(w);punct.append(p)
g=[[] for _ in range(2*len(ids))];marked=bytearray(len(g));q=deque()
for i in range(len(words)-1):
 if punct[i]=='.':continue
 a=2*ids[words[i]];b=2*ids[words[i+1]]+1;g[a].append(b);g[b].append(a)
 if punct[i]==',':
  for x in (a,b):
   if not marked[x]:marked[x]=1;q.append(x)
while q:
 x=q.popleft()
 for y in g[x]:
  if not marked[y]:marked[y]=1;q.append(y)
print(' '.join(w+('.' if punct[i]=='.' else ',' if marked[2*ids[w]] else '') for i,w in enumerate(words)))
