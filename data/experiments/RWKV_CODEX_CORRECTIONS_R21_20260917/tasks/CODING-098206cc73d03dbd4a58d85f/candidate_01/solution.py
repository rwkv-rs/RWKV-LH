import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);k=next(it);a=[[next(it) for _ in range(m)] for _ in range(n)]
if n>m:a=list(map(list,zip(*a)));n,m=m,n
ans=0
for top in range(n):
 sums=[0]*m
 for bottom in range(top,n):
  seen={0:1};p=0;row=a[bottom]
  for j in range(m):
   sums[j]+=row[j];p=(p+sums[j])%k;cnt=seen.get(p,0);ans+=cnt;seen[p]=cnt+1
print(ans)
