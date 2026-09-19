import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);queries=[(next(it),next(it)) for _ in range(t)];groups={};mod=1000000007
for n,k in queries:groups[k]=max(groups.get(k,0),n)
answers={}
for k,maximum in groups.items():
 result=[1]+[0]*maximum
 if k==1:answers[k]=result;continue
 for length in range(1,min(maximum,k-1)+1):result[length]=pow(2,length,mod)
 if maximum<k:answers[k]=result;continue
 def palindrome(x,length):return all(((x>>j)^(x>>(length-1-j)))&1==0 for j in range(length//2))
 size=1<<k;mask=size-1;valid=[x for x in range(size) if not palindrome(x,k)];dp=[0]*size;edges={}
 for x in valid:
  dp[x]=1;edges[x]=[y for bit in (0,1) if not palindrome((x<<1)|bit,k+1) and not palindrome((y:=((x<<1)|bit)&mask),k)]
 result[k]=sum(dp)
 for length in range(k+1,maximum+1):
  nxt=[0]*size
  for x in valid:
   if dp[x]:
    for y in edges[x]:nxt[y]=(nxt[y]+dp[x])%mod
  dp=nxt;result[length]=sum(dp)%mod
 answers[k]=result
print('\n'.join(str(answers[k][n]) for n,k in queries))
