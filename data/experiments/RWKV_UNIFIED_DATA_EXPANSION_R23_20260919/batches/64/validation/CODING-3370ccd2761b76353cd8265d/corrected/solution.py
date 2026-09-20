import sys
v=sys.stdin.buffer.read().split();p=1;MOD=1000000007;out=[]
for _ in range(int(v[0])):
 n=int(v[p]);p+=1;graph=[[] for _ in range(n)]
 for _ in range(n-1):
  a,sign,b=v[p:p+3];p+=3;a=int(a);b=int(b);less=sign==b'<';graph[a].append((b,less));graph[b].append((a,not less))
 f=[1]*(n+1);g=[1]*(n+1)
 for i in range(1,n+1):f[i]=f[i-1]*i%MOD
 g[n]=pow(f[n],MOD-2,MOD)
 for i in range(n,0,-1):g[i-1]=g[i]*i%MOD
 def choose(a,b):return f[a]*g[b]%MOD*g[a-b]%MOD
 parent=[-1]*n;order=[0];relation=[False]*n
 for u in order:
  for w,less in graph[u]:
   if w!=parent[u]:parent[w]=u;relation[w]=less;order.append(w)
 dp=[None]*n
 for u in reversed(order):
  current=[1]
  for w,unused in graph[u]:
   if parent[w]!=u:continue
   child=dp[w];A=len(current);B=len(child);prefix=[0]
   for number in child:prefix.append((prefix[-1]+number)%MOD)
   merged=[0]*(A+B)
   for i,number in enumerate(current):
    if not number:continue
    for t in range(B+1):
     ways=(prefix[B]-prefix[t])%MOD if relation[w] else prefix[t]
     if ways:merged[i+t]=(merged[i+t]+number*ways%MOD*choose(i+t,t)%MOD*choose(A+B-i-t-1,B-t))%MOD
   current=merged;dp[w]=None
  dp[u]=current
 out.append(str(sum(dp[0])%MOD))
print('\n'.join(out))
