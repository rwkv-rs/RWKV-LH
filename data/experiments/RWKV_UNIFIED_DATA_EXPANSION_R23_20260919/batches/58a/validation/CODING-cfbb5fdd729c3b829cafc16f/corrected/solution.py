import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k,A=v[:3];level=v[3::2];loyalty=[x//10 for x in v[4::2]];size=1<<n;payoff=[0.0]*size
for mask in range(size):
 if mask.bit_count()>n//2:payoff[mask]=1.0
 else:payoff[mask]=A/(A+sum(level[i] for i in range(n) if not(mask>>i&1)))
best=0.0
prob=[0.0]*n
def solve(i,left):
 global best
 if i==n:
  weights=[1.0]
  for p in prob:weights=[x*(1-p) for x in weights]+[x*p for x in weights]
  best=max(best,sum(x*y for x,y in zip(weights,payoff)));return
 for give in range(min(left,10-loyalty[i])+1):prob[i]=(loyalty[i]+give)/10;solve(i+1,left-give)
solve(0,k);print('%.10f'%best)
