import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=[x-1 for x in v[1:]]+[n-1];size=1
while size<n:size*=2
tree=[-1]*(2*size)
def better(x,y):
 if x<0:return y
 if y<0:return x
 return x if a[x]>=a[y] else y
def put(i):
 p=size+i;tree[p]=i;p//=2
 while p:tree[p]=better(tree[2*p],tree[2*p+1]);p//=2
def query(l,r):
 l+=size;r+=size;answer=-1
 while l<r:
  if l&1:answer=better(answer,tree[l]);l+=1
  if r&1:r-=1;answer=better(answer,tree[r])
  l//=2;r//=2
 return answer
dp=[0]*n;put(n-1)
for i in range(n-2,-1,-1):
 j=query(i+1,a[i]+1);dp[i]=dp[j]+n-i-1-(a[i]-j);put(i)
print(sum(dp))
