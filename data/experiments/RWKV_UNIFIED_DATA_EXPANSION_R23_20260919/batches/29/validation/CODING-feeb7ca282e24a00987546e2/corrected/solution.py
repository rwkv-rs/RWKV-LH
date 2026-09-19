import sys
t1,t2,x1,x2,t0=map(int,sys.stdin.read().split())
if t1==t2:print(x1,x2)
elif t0==t1:print(x1,0)
else:
 cold=t0-t1;hot=t2-t0;best_a=0;best_b=x2;best_excess=hot*x2;best_total=x2
 for b in range(1,x2+1):
  a=min(x1,hot*b//cold);excess=hot*b-cold*a;total=a+b
  if excess*best_total<best_excess*total or (excess*best_total==best_excess*total and total>best_total):best_a,best_b,best_excess,best_total=a,b,excess,total
 print(best_a,best_b)
