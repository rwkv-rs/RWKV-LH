import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,p=v[:2];colors=v[2:];mod=1000000007
dp={(0,0):1};power=1
for i,c in enumerate(colors):
 nxt={}
 for (flags,parity),ways in dp.items():
  for color in ((0,1) if c==-1 else (c,)):
   if flags&(1<<(1-color)):
    factor=power*500000004%mod;options=(0,1)
   else:factor=power;options=(1,)
   for bit in options:
    key=(flags|((1<<color) if bit else 0),parity^bit)
    nxt[key]=(nxt.get(key,0)+ways*factor)%mod
 dp=nxt;power=power*2%mod
print(sum(ways for (flags,parity),ways in dp.items() if parity==p)%mod)
