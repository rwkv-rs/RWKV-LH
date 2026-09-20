import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,s,e=v[:3];s-=1;e-=1;x=v[3:3+n];a=v[3+n:3+2*n];b=v[3+2*n:3+3*n];c=v[3+3*n:3+4*n];d=v[3+4*n:3+5*n];INF=10**30;dp=[0]+[INF]*(n+1)
for i in range(n):
 new=[INF]*(n+2);seenS=s<i;seenE=e<i
 for j in range(i+1):
  value=dp[j]
  if value==INF:continue
  if i==s:
   new[j+1]=min(new[j+1],value+d[i]-x[i])
   if j>seenS:new[j]=min(new[j],value+c[i]+x[i])
  elif i==e:
   new[j+1]=min(new[j+1],value+b[i]-x[i])
   if j>seenE:new[j]=min(new[j],value+a[i]+x[i])
  else:
   new[j+1]=min(new[j+1],value+b[i]+d[i]-2*x[i])
   if j>1:new[j-1]=min(new[j-1],value+a[i]+c[i]+2*x[i])
   if j>seenE:new[j]=min(new[j],value+a[i]+d[i])
   if j>seenS:new[j]=min(new[j],value+b[i]+c[i])
 if i<n-1 and s<=i and e<=i:new[1]=INF
 dp=new
print(dp[1])
