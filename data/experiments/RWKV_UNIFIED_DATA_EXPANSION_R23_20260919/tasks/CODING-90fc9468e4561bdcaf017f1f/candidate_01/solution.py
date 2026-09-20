import sys
values=iter(map(int,sys.stdin.buffer.read().split()));n=next(values);m=next(values);rank=next(values);length=n+m-1;priority=[n*m+1]*length
for i in range(n):
 for j in range(m):priority[i+j]=min(priority[i+j],next(values))
fixed=[0]*length

def count():
 dp=[1]
 for pos,step in enumerate(fixed):
  remaining=length-pos-1;limit=min(pos+1,remaining);following=[0]*(limit+1)
  for height,ways in enumerate(dp):
   if ways:
    if step>=0 and height+1<=limit:following[height+1]+=ways
    if step<=0 and 0<=height-1<=limit:following[height-1]+=ways
  dp=following
 return dp[0]
for pos in sorted(range(length),key=priority.__getitem__):
 fixed[pos]=1;ways=count()
 if rank>ways:rank-=ways;fixed[pos]=-1
word=''.join('(' if x==1 else ')' for x in fixed)
print('\n'.join(word[i:i+m] for i in range(n)))
