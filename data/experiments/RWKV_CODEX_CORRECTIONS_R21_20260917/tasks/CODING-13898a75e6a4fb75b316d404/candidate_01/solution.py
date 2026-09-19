import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);dp={}
 for _ in range(n):
  x=next(it);nxt=dp.copy();nxt[x]=nxt.get(x,0)+1
  for g,count in dp.items():
   d=math.gcd(g,x);nxt[d]=nxt.get(d,0)+count
  dp=nxt
 out.append(str(dp.get(1,0)))
print('\n'.join(out))
