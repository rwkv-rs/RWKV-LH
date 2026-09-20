import sys
it=iter(map(int,sys.stdin.buffer.read().split()));m=next(it);n=next(it);days=[]
for _ in range(m):
 size=next(it);mask=0
 for j in range(size):mask|=1<<(next(it)-1)
 days.append(mask)
print('possible' if all(a&b for i,a in enumerate(days) for b in days[:i]) else 'impossible')
