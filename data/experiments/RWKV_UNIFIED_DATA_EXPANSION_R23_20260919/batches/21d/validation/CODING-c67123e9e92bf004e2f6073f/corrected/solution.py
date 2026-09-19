import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for first in v:
 if first==0:break
 cycles=[first]
 for x in v:
  if x==0:break
  cycles.append(x)
 answer=None
 for t in range(2*min(cycles),18001):
  if all(t%(2*c)<c-5 for c in cycles):answer=t;break
 if answer is None:out.append('Signals fail to synchronise in 5 hours.')
 else:out.append(f'{answer//3600:02d}:{answer//60%60:02d}:{answer%60:02d}')
print('\n'.join(out))
