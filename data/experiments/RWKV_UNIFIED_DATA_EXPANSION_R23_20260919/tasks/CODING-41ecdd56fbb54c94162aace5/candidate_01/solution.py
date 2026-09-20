import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);s=v[1];runs=[]
for c in s:
 if not runs or runs[-1]!=c:runs.append(c)
MOD=1000000007;m=len(runs);total=[0]*(m+1);total[0]=1;ending={c:[0]*(m+1) for c in set(runs)}
for length,c in enumerate(runs,1):
 old=ending[c]
 for r in range(length,0,-1):
  new=(total[r-1]-old[r-1])%MOD;total[r]=(total[r]+new-old[r])%MOD;old[r]=new
answer=0;choose=1;inverse=[0]*(m+1)
if m:inverse[1]=1
for i in range(2,m+1):inverse[i]=MOD-(MOD//i)*inverse[MOD%i]%MOD
for r in range(1,m+1):
 answer=(answer+choose*total[r])%MOD
 choose=choose*(n-r)%MOD*inverse[r]%MOD
print(answer)
