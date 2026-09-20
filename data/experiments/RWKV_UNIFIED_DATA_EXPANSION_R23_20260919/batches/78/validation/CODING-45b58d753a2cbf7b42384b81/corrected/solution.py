import sys,math
v=sys.stdin.buffer.read().split();p=1;out=[]
for _ in range(int(v[0])):
 n=int(v[p]);s=v[p+1];width,minimum,maximum=map(int,v[p+2:p+5]);p+=5;maximum+=1;minimum+=1;mask=(1<<(maximum+1))-1;dp=[{} for _ in range(n+1)];dp[0][0]=1
 for start in range(n):
  states=dp[start]
  if not states:continue
  number=0
  for end in range(start+1,min(n,start+width)+1):
   number=number*10+s[end-1]-48;target=dp[end];least=max(0,minimum-(n-end));most=maximum-(n-end+width-1)//width;allowed=((1<<(most+1))-1) if most>=0 else 0
   if least:allowed&=~((1<<least)-1)
   for g,counts in states.items():
    nextcounts=(counts<<1)&mask&allowed
    if nextcounts:
     nextg=math.gcd(g,number);target[nextg]=target.get(nextg,0)|nextcounts
  dp[start]={}
 out.append(str(max(dp[n])))
print('\n'.join(out))
