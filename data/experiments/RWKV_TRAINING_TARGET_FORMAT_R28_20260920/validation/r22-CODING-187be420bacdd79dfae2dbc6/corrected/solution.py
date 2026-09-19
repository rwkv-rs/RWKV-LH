import sys
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];limit=max(a);weighted=[0]*(limit+1)
for x in a:weighted[x]+=x
exact=[0]*(limit+1);answer=0
for d in range(limit,0,-1):
 total=sum(weighted[d::d]);value=total*total-sum(exact[2*d::d]);exact[d]=value;answer+=value//d
print(answer)
