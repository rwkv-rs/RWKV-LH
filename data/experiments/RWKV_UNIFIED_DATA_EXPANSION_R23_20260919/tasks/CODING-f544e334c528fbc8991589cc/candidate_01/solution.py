import sys
mod=1000000007;v=iter(map(int,sys.stdin.read().split()));cases=[(next(v),next(v),next(v)) for _ in range(next(v))];maximum=max(n*m for n,m,r in cases);fact=[1]*(maximum+1)
for i in range(1,maximum+1):fact[i]=fact[i-1]*i%mod
inverse=[1]*(maximum+1);inverse[maximum]=pow(fact[maximum],mod-2,mod)
for i in range(maximum,0,-1):inverse[i-1]=inverse[i]*i%mod
def choose(n,k):return 0 if k<0 or k>n else fact[n]*inverse[k]%mod*inverse[n-k]%mod
out=[]
for n,m,r in cases:
 answer=0
 for rows in range(n+1):
  cr=choose(n,rows)
  for cols in range(m+1):
   term=cr*choose(m,cols)%mod*choose((n-rows)*(m-cols),r)%mod
   answer+=term if (rows+cols)%2==0 else -term
 out.append(str(answer%mod))
print('\n'.join(out))
