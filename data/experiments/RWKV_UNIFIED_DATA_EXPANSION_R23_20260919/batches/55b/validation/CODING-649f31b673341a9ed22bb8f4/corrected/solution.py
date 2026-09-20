import sys
v=sys.stdin.read().split();n,x=map(int,v[:2]);N=1
while N<=x:N*=2
p=list(map(float,v[2:]))+[0.0]*(N-x-1);step=1
while step<N:
 for start in range(0,N,2*step):
  for j in range(start,start+step):a,b=p[j],p[j+step];p[j]=a+b;p[j+step]=a-b
 step*=2
lose=sum(value**n for value in p)/N
print(f'{max(0.0,min(1.0,1.0-lose)):.8f}')
