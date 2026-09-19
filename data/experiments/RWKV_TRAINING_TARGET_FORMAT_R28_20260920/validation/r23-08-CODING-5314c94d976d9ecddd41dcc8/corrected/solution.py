import sys
it=iter(map(int,sys.stdin.buffer.read().split()));x=next(it);k=next(it);known=[False]*(x+1)
for _ in range(k):
 kind=next(it);known[next(it)]=True
 if kind==1:known[next(it)]=True
low=0;high=0;run=0
for i in range(1,x+1):
 if i<x and not known[i]:run+=1
 else:low+=(run+1)//2;high+=run;run=0
print(low,high)
