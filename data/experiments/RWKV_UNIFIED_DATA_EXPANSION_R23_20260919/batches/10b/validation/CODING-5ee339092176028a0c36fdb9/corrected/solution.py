import sys
s,t=sys.stdin.read().split();n=len(s);m=len(t)
if m>n:print(0);raise SystemExit
periods=[d for d in range(1,m) if t[d:]==t[:-d]];ending=[-10**9]*(n-m+1);best=[0]*(n-m+1)
for i in range(n-m+1):
 value=best[i-1] if i else 0
 if all(s[i+j]=='?' or s[i+j]==t[j] for j in range(m)):
  candidate=1+(best[i-m] if i>=m else 0)
  for d in periods:
   if d>i:break
   candidate=max(candidate,ending[i-d]+1)
  ending[i]=candidate;value=max(value,candidate)
 best[i]=value
print(best[-1])
