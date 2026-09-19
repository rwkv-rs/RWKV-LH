import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
while True:
 try:n=next(it);q=next(it)
 except StopIteration:break
 if n==q==0:break
 w=[next(it) for _ in range(n)];dp=[0]*(n+1);dp[0]=1
 for i,x in enumerate(w,1):
  for k in range(i,0,-1):dp[k]|=dp[k-1]<<x
 total=sum(w)
 for _ in range(q):
  x=next(it);counts=[str(k) for k in range(n+1) if 0<=x<=total and (dp[k]>>x)&1]
  out.append(' '.join(counts) if counts else "That's impossible!")
print('\n'.join(out))
