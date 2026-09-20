import sys,math
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
while True:
 try:n=next(v)
 except StopIteration:break
 if n==0:break
 groups={}
 for _ in range(n):
  d,t=next(v),next(v);values=[next(v) for _ in range(d)];target=groups.setdefault(d,[0]*d)
  for j in range(d):target[j]+=values[(j+t)%d]
 independent=0
 for prime in (13,17,19,23):
  if prime in groups:independent+=max(groups.pop(prime))
 cycle=1
 for d in groups:cycle=math.lcm(cycle,d)
 totals=[0]*cycle
 for d,values in groups.items():
  for i in range(cycle):totals[i]+=values[i%d]
 out.append(str(independent+max(totals)))
print('\n'.join(out))
