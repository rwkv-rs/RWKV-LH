import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n,K=next(it),next(it);a=[next(it) for _ in range(n)];prev=[0]*n;last={}
for i,x in enumerate(a):prev[i]=last.get(x,-1)+1;last[x]=i
negative=-10**9;dp=[0]+[negative]*n
for box in range(1,K+1):
 maximum=[negative]*(4*n);lazy=[0]*(4*n)
 def build(p,l,r):
  if l==r:maximum[p]=dp[l];return
  mid=(l+r)//2;build(p*2,l,mid);build(p*2+1,mid+1,r);maximum[p]=max(maximum[p*2],maximum[p*2+1])
 def add(p,l,r,L,R):
  if L<=l and r<=R:maximum[p]+=1;lazy[p]+=1;return
  mid=(l+r)//2
  if L<=mid:add(p*2,l,mid,L,R)
  if R>mid:add(p*2+1,mid+1,r,L,R)
  maximum[p]=lazy[p]+max(maximum[p*2],maximum[p*2+1])
 def query(p,l,r,R):
  if r<=R:return maximum[p]
  mid=(l+r)//2;z=query(p*2,l,mid,R)
  if R>mid:z=max(z,query(p*2+1,mid+1,r,R))
  return z+lazy[p]
 build(1,0,n-1);new=[negative]*(n+1)
 for i in range(n):add(1,0,n-1,prev[i],i);new[i+1]=query(1,0,n-1,i)
 dp=new
print(dp[n])
