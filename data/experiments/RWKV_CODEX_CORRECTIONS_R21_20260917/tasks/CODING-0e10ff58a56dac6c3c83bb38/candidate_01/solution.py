import sys,math
n,k=map(int,sys.stdin.buffer.read().split());mod=998244353;inv=[0]+[pow(i,mod-2,mod) for i in range(1,n+1)];cache={};answer=0
def visit(left,minimum,lcm,weight,last,count):
 global answer
 if left==0:
  power=cache.get(lcm)
  if power is None:power=pow(lcm,k,mod);cache[lcm]=power
  answer=(answer+weight*power)%mod;return
 for length in range(minimum,left+1):
  if left!=length and left-length<length:continue
  multiplicity=count+1 if length==last else 1
  visit(left-length,length,lcm//math.gcd(lcm,length)*length,weight*inv[length]%mod*inv[multiplicity]%mod,length,multiplicity)
visit(n,1,1,1,0,0);print(answer*math.factorial(n)%mod)
