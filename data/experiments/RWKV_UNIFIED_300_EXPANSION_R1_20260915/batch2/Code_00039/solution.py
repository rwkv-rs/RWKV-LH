import sys
a=iter(map(int,sys.stdin.buffer.read().split()));n=next(a);g=[[] for _ in range(n)]
for e in range(n-1):
    u,v=next(a)-1,next(a)-1;g[u].append((v,1<<e));g[v].append((u,1<<e))
x=[0]*n;stack=[(0,-1)]
while stack:
    u,p=stack.pop()
    for v,b in g[u]:
        if v!=p:x[v]=x[u]^b;stack.append((v,u))
m=next(a);paths=[x[next(a)-1]^x[next(a)-1] for _ in range(m)];union=[0]*(1<<m);ans=1<<(n-1)
for mask in range(1,1<<m):
    bit=mask&-mask;u=union[mask^bit]|paths[bit.bit_length()-1];union[mask]=u
    value=1<<(n-1-u.bit_count());ans+=-value if mask.bit_count()%2 else value
print(ans)
