import sys
v=sys.stdin.buffer.read().split();m,d=map(int,v[:2]);a=v[2].decode();b=v[3].decode();mod=1000000007
moves=[[ (r*10+x)%m for r in range(m)] for x in range(10)]
def count(bound):
 dp=[0]*m;equal=0;valid=True
 for i,ch in enumerate(bound):
  limit=int(ch);digits=(d,) if i%2 else tuple(x for x in range(1 if i==0 else 0,10) if x!=d);nxt=[0]*m
  for x in digits:
   dest=moves[x]
   for r,w in enumerate(dp):
    if w:nxt[dest[r]]+=w
  if valid:
   for x in digits:
    if x<limit:nxt[(equal*10+x)%m]+=1
   valid=limit in digits;equal=(equal*10+limit)%m
  dp=[w%mod for w in nxt]
 return (dp[0]+int(valid and equal==0))%mod
valid=all((int(c)==d) if i%2 else (int(c)!=d) for i,c in enumerate(a));remainder=0
for c in a:remainder=(10*remainder+int(c))%m
print((count(b)-count(a)+int(valid and remainder==0))%mod)
