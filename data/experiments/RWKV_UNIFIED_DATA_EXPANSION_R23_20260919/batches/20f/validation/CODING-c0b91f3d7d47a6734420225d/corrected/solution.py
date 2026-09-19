import sys
v=iter(map(int,sys.stdin.read().split()));n=next(v);a=sorted((next(v),next(v),i) for i in range(n));suffix=[10**30]*(n+1)
for i in range(n-1,-1,-1):suffix[i]=min(suffix[i+1],a[i][1])
answer=[0]*n;left=0;maximum=-1
for i,(_,rating,index) in enumerate(a):
 maximum=max(maximum,rating)
 if maximum<suffix[i+1]:
  for j in range(left,i+1):answer[a[j][2]]=i
  left=i+1
print('\n'.join(map(str,answer)))
