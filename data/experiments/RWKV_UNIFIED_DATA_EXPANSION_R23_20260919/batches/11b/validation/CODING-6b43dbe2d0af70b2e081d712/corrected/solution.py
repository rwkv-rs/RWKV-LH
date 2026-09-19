import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 a=[0]+[next(it) for _ in range(5)];b=[0]+[next(it) for _ in range(5)];possible=True
 for weight,capacities in ((5,(5,)),(4,(4,5)),(3,(3,5,4))):
  for capacity in capacities:
   take=min(a[weight],b[capacity]);a[weight]-=take;b[capacity]-=take;b[capacity-weight]+=take
  if a[weight]:possible=False
 slots=sum((capacity//2)*b[capacity] for capacity in range(1,6));space=sum(capacity*b[capacity] for capacity in range(1,6));possible=possible and a[2]<=slots and a[1]+2*a[2]<=space;out.append('Yes' if possible else 'No')
print('\n'.join(out))
