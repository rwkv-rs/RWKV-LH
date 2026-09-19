import sys,math
period=9*math.lcm(*range(1,10));marked=bytearray(period+1)
for d in range(1,10):
 for x in range(d*d,period+1,9*d):marked[x]=1
prefix=[0]*(period+1)
for i in range(1,period+1):prefix[i]=prefix[i-1]+marked[i]
def count(x):return 0 if x<=0 else (x//period)*prefix[-1]+prefix[x%period]
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 l=next(v);r=next(v);out.append(str(count(r)-count(l-1)))
print('\n'.join(out))
