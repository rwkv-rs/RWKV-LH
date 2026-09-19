import sys
out=[]
for n in map(int,sys.stdin.read().split()):
 if n==-1:break
 digits=[];x=n
 while x:digits.append(x%5);x//=5
 dp={(0,True):1}
 for pos in range(len(digits)-1,-1,-1):
  nd={};bound=digits[pos]
  for (parity,tight),count in dp.items():
   for d in range((bound if tight else 4)+1):
    key=(parity^((pos*d)&1),tight and d==bound);nd[key]=nd.get(key,0)+count
  dp=nd
 out.append(str(sum(c for (p,t),c in dp.items() if p==0)))
print('\n'.join(out))
