import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);shift=0;low=-10**30;high=10**30
for _ in range(n):
 a=next(it);kind=next(it)
 if kind==1:shift+=a;low+=a;high+=a
 elif kind==2:low=max(low,a);high=max(high,a)
 else:low=min(low,a);high=min(high,a)
q=next(it);print('\n'.join(str(min(high,max(low,next(it)+shift))) for _ in range(q)))
