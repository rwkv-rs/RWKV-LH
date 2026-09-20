import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n,K,D=next(it),next(it),next(it);x=[next(it) for i in range(n)];lanes=[next(it) for i in range(n)];last=-D;answer=K
 for i in range(1,n):
  if lanes[i]==lanes[i-1]:continue
  switch=max(x[i-1]+1,last+D)
  if switch>=x[i]:answer=x[i];break
  last=switch
 out.append(str(answer))
print('\n'.join(out))
