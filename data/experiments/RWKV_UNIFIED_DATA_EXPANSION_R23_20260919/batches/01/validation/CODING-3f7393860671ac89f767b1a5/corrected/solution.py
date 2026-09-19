import sys
a=list(map(int,sys.stdin.buffer.read().split()));n=a[0];b=a[1:n+1];need=a[n+1:2*n+1];d=[b[i]-need[i] for i in range(n)];parents=[0]*n;factor=[1]*n
for i in range(1,n):parents[i]=a[2*n+1+2*(i-1)]-1;factor[i]=a[2*n+2+2*(i-1)]
limit=sum(b)
for i in range(n-1,0,-1):
 v=d[i] if d[i]>=0 else d[i]*factor[i]
 if v < -limit:print('NO');break
 d[parents[i]]+=v
else:print('YES' if d[0]>=0 else 'NO')
