import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);q=next(it);last={};limit=[0]*(n+1);worst=0
for i in range(1,n+1):
 x=next(it);worst=max(worst,last.get(x,0));limit[i]=worst;last[x]=i
out=[]
for _ in range(q):
 left=next(it);right=next(it);out.append('Yes' if limit[right]<left else 'No')
print('\n'.join(out))
