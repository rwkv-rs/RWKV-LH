import sys,math
v=iter(sys.stdin.read().split());out=[]
while True:
 try:n=int(next(v))
 except StopIteration:break
 points=[(float(next(v)),float(next(v))) for i in range(n)]
 def distance(i,j):return math.hypot(points[i][0]-points[j][0],points[i][1]-points[j][1])
 if n<2:out.append('0.00');continue
 dp=[distance(0,1)]
 for j in range(2,n):
  latest=min(dp[i]+distance(i,j) for i in range(j-1));edge=distance(j-1,j);dp=[x+edge for x in dp]+[latest]
 out.append(f'{dp[-1]+distance(n-2,n-1):.2f}')
print('\n'.join(out))
