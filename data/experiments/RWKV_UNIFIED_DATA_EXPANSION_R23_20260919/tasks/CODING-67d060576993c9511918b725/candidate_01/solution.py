import sys
v=iter(map(int,sys.stdin.buffer.read().split()));cases=[];limit=0
for _ in range(next(v)):
 n,m=next(v),next(v);a=[];b=[]
 for i in range(m):a.append(next(v));b.append(next(v))
 cases.append((n,m,a,b));limit=max(limit,2*n-2)
mod=998244353;fac=[1]*(limit+1)
for i in range(1,limit+1):fac[i]=fac[i-1]*i%mod
inv=[1]*(limit+1);inv[limit]=pow(fac[limit],mod-2,mod)
for i in range(limit,0,-1):inv[i-1]=inv[i]*i%mod
out=[]
for n,m,a,b in cases:
 mat=[[fac[n-1+y-x]*inv[n-1]%mod*inv[y-x]%mod if y>=x else 0 for y in b] for x in a];answer=1
 for col in range(m):
  pivot=next((r for r in range(col,m) if mat[r][col]),None)
  if pivot is None:answer=0;break
  if pivot!=col:mat[col],mat[pivot]=mat[pivot],mat[col];answer=-answer
  row=mat[col];value=row[col];answer=answer*value%mod;reciprocal=pow(value,mod-2,mod)
  for r in range(col+1,m):
   factor=mat[r][col]*reciprocal%mod
   if factor:
    other=mat[r]
    for k in range(col+1,m):other[k]=(other[k]-factor*row[k])%mod
    other[col]=0
 out.append(str(answer%mod))
print('\n'.join(out))
