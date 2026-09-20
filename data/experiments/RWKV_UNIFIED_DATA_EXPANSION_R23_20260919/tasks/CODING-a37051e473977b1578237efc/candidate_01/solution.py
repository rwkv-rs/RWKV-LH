import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];fav=bytearray(1<<n)
for team in v[2:2+k]:fav[team-1]=1
transitions={}
for a in range(4):
 u1,v1=divmod(a,2)
 for b in range(4):
  u2,v2=divmod(b,2);best={}
  for upper,loser in ((u1,u2),(u2,u1)):
   for lower in (v1,v2):
    score=(u1|u2)+(v1|v2)+(loser|lower)
    for survivor in (loser,lower):
     state=2*upper+survivor;best[state]=max(best.get(state,-1),score)
  transitions[a,b]=list(best.items())
level=[]
for i in range(0,len(fav),2):
 a=fav[i];b=fav[i+1];dp=[-10**9]*4;dp[2*a+b]=dp[2*b+a]=a|b;level.append(dp)
while len(level)>1:
 following=[]
 for i in range(0,len(level),2):
  left,right=level[i:i+2];dp=[-10**9]*4
  for a,x in enumerate(left):
   if x<0:continue
   for b,y in enumerate(right):
    if y<0:continue
    base=x+y
    for state,bonus in transitions[a,b]:
     value=base+bonus
     if value>dp[state]:dp[state]=value
  following.append(dp)
 level=following
print(max(score+bool(state) for state,score in enumerate(level[0])))
