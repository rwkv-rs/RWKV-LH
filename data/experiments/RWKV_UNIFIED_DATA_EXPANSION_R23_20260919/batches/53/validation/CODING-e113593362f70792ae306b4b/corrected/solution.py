import sys,math
n,m,p=map(int,sys.stdin.buffer.read().split());inverse=[0]+[pow(i,p-2,p) for i in range(1,n+1)];gcd=[[math.gcd(i,j) for j in range(n+1)] for i in range(n+1)];counts=[0]*(n+1);parts=[];answer=0;powers=[1]
for _ in range(n*(n-1)//2):powers.append(powers[-1]*m%p)
def visit(rem,minimum,orbits,weight):
 global answer
 if not rem:answer=(answer+weight*powers[orbits])%p;return
 for length in range(minimum,rem+1):
  extra=length//2+sum(gcd[length][old] for old in parts);counts[length]+=1;parts.append(length);visit(rem-length,length,orbits+extra,weight*inverse[length]%p*inverse[counts[length]]%p);parts.pop();counts[length]-=1
visit(n,1,0,1);print(answer)
