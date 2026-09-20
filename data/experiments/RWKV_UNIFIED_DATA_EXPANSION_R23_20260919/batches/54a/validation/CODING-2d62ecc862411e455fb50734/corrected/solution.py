import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));MOD=10**9+7;out=[]
def compositions(total,count):
 if count==0:return int(total==0)
 return math.comb(total-1,count-1) if total>=count else 0
for _ in range(next(it)):
 N,S=next(it),next(it);a=[next(it) for i in range(N)];known=[x for x in a if x!=-1];missing=N-len(known);remaining=S-sum(known);ways=compositions(remaining,missing);fixed=sum(math.gcd(known[i],known[j]) for i in range(len(known)) for j in range(i+1,len(known)));answer=fixed*ways
 if missing:
  for x in range(1,remaining+1):answer+=missing*sum(math.gcd(x,y) for y in known)*compositions(remaining-x,missing-1)
 if missing>=2:
  both=0
  for x in range(1,remaining):
   for y in range(1,remaining-x+1):both+=math.gcd(x,y)*compositions(remaining-x-y,missing-2)
  answer+=missing*(missing-1)//2*both
 out.append(str(answer%MOD))
print('\n'.join(out))
