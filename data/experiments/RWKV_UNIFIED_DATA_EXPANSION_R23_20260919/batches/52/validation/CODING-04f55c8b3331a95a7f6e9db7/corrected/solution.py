import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];answer=[0]*(n+1);cache={}
def solve(k):
 if k in cache:return cache[k]
 groups=1;seen=set()
 for x in a:
  if x not in seen:
   if len(seen)==k:groups+=1;seen={x}
   else:seen.add(x)
 cache[k]=groups;return groups
def fill(l,r,lo,hi):
 if lo==hi:
  answer[l:r+1]=[lo]*(r-l+1);return
 if l==r:answer[l]=solve(l);return
 mid=(l+r)//2;x=solve(mid);answer[mid]=x
 if l<mid:fill(l,mid-1,lo,x)
 if mid<r:fill(mid+1,r,x,hi)
fill(1,n,solve(1),1)
print(*answer[1:])
