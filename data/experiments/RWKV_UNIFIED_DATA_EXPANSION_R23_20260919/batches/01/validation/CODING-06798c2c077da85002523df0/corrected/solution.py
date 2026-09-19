import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];p=[0]
for x in a:p.append(p[-1]+x)
mod=1000000007;prev=[0]*(n+1);prev[0]=1;answer=0
for k in range(1,n+1):
 sums=[0]*k;cur=[0]*(n+1)
 for i in range(k,n+1):
  r=p[i-1]%k;sums[r]=(sums[r]+prev[i-1])%mod;cur[i]=sums[p[i]%k]
 answer=(answer+cur[n])%mod;prev=cur
print(answer)
