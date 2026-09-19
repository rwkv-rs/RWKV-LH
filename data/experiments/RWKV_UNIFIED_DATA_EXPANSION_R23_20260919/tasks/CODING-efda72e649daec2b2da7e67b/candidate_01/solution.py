import sys
mod=1000000007;v=iter(map(int,sys.stdin.read().split()));out=[];cache={}
def multiply(a,b):
 return [[sum(a[i][z]*b[z][j] for z in range(10))%mod for j in range(10)] for i in range(10)]
for _ in range(next(v)):
 n=next(v);k=next(v);powers=cache.setdefault(k,[[[int(abs(i-j)>=k) for j in range(10)] for i in range(10)]])
 vector=[0]+[1]*9;exponent=n-1;bit=0
 while exponent:
  if bit==len(powers):powers.append(multiply(powers[-1],powers[-1]))
  if exponent&1:vector=[sum(vector[i]*powers[bit][i][j] for i in range(10))%mod for j in range(10)]
  exponent//=2;bit+=1
 out.append(str(sum(vector)%mod))
print('\n'.join(out))
