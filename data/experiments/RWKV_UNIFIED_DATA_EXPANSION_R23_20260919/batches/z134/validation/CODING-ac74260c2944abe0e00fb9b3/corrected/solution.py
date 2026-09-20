import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];ends=v[2:3+m];ranks=v[3+m:3+2*m]
def solve(left,height):
 right=left+(1<<height);first=bisect.bisect_right(ends,left)-1;last=bisect.bisect_left(ends,right)-1;size=n-height+1
 if first==last:
  stated=ranks[first];base=(1<<(height-n+stated-1)) if stated>n-height else 0;result=[base]*size
  if stated<size:result[stated]+=1
  return result
 middle=left+(1<<(height-1));a=solve(left,height-1);b=solve(middle,height-1);lose=n-height+1;return [max(a[i]+b[lose],b[i]+a[lose]) for i in range(size)]
print((1<<n)-solve(0,n)[0])
