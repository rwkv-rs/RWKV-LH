import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);reverse=[[] for _ in range(n)]
for _ in range(m):a=next(it)-1;b=next(it)-1;reverse[b].append(a)
answer=[0]*n
for target in range(n-1,-1,-1):
 if answer[target]:continue
 answer[target]=target+1;stack=[target]
 while stack:
  x=stack.pop()
  for y in reverse[x]:
   if not answer[y]:answer[y]=target+1;stack.append(y)
print(' '.join(map(str,answer)))
