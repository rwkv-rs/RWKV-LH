import sys,functools
v=list(map(int,sys.stdin.buffer.read().split()))
def game(p):
 q=1-p
 return p**4*(1+4*q+10*q*q)+20*p**3*q**3*p*p/(p*p+q*q)
def winset(first,second):
 deuce=first*second/(first*second+(1-first)*(1-second));dp=[[0.0]*6 for _ in range(6)];dp[0][0]=1.0;answer=0.0
 for a in range(6):
  for b in range(6):
   mass=dp[a][b]
   if a==b==5:answer+=mass*deuce;continue
   p=first if (a+b)%2==0 else second
   if a==5:answer+=mass*p
   else:dp[a+1][b]+=mass*p
   if b<5:dp[a][b+1]+=mass*(1-p)
 return answer
@functools.lru_cache(None)
def match(m,y):
 serve=game(m/100);receive=game(y/100);first=winset(serve,receive);second=winset(receive,serve);dp=[[0.0]*3 for _ in range(3)];dp[0][0]=1.0;answer=0.0
 for a in range(3):
  for b in range(3):
   p=first if (a+b)%2==0 else second;mass=dp[a][b]
   if a==2:answer+=mass*p
   else:dp[a+1][b]+=mass*p
   if b<2:dp[a][b+1]+=mass*(1-p)
 return answer*100
for i in range(v[0]):print(f'Case #{i+1}: {match(v[1+2*i],v[2+2*i]):.4f}%')
