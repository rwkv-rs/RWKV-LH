import sys
a,b,p,x=map(int,sys.stdin.read().split());period=p*(p-1);inverse=pow(a,p-2,p);target=b;answer=0
for r in range(p-1):
 first=r+(p-1)*((r-target)%p)
 if first<=x:answer+=(x-first)//period+1
 target=target*inverse%p
print(answer)
