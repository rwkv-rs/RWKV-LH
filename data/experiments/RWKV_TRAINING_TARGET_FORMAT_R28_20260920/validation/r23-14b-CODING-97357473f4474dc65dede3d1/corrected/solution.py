import sys
v=list(map(int,sys.stdin.read().split()));out=[]
for n in v[1:1+v[0]]:
 tax=0
 for slab in range(1,6):tax+=max(0,min(250000,n-250000*slab))*(slab*5)//100
 tax+=max(0,n-1500000)*30//100
 out.append(str(n-tax))
print('\n'.join(out))
