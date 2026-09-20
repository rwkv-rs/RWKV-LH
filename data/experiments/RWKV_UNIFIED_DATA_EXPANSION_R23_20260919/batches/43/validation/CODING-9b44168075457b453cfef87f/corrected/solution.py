import sys
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n,k,q=next(it),next(it),next(it);a=[next(it) for _ in range(n)];mod=1000000007;dp=[array('I',[0]+[1]*n+[0])]
for step in range(k):
 prev=dp[-1];row=array('I',[0])
 for i in range(1,n+1):row.append((prev[i-1]+prev[i+1])%mod)
 row.append(0);dp.append(row)
weights=[0]*(n+2)
for step in range(k//2+1):
 left,right=dp[step],dp[k-step];factor=1 if step*2==k else 2
 for i in range(1,n+1):weights[i]=(weights[i]+factor*left[i]*right[i])%mod
answer=sum(value*weights[i+1] for i,value in enumerate(a))%mod;out=[]
for _ in range(q):
 i,x=next(it)-1,next(it);answer=(answer+(x-a[i])*weights[i+1])%mod;a[i]=x;out.append(str(answer))
print('\n'.join(out))
