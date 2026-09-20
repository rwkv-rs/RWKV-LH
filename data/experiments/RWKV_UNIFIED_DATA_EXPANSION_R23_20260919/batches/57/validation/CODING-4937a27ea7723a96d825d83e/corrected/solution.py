import sys
v=list(map(int,sys.stdin.buffer.read().split()));r,c=v[:2];a=[v[2+i*c:2+(i+1)*c] for i in range(r)];rm=list(map(max,a));cm=[max(a[i][j] for i in range(r)) for j in range(c)];edges=[[j for j in range(c) if a[i][j]>0 and rm[i]==cm[j] and rm[i]>1] for i in range(r)];match=[-1]*c
def augment(i,seen):
 for j in edges[i]:
  if seen[j]:continue
  seen[j]=True
  if match[j]<0 or augment(match[j],seen):match[j]=i;return True
 return False
saving=0
for i in range(r):
 if augment(i,[False]*c):saving+=rm[i]-1
minimum=sum(x>0 for row in a for x in row)+sum(max(0,x-1) for x in rm)+sum(max(0,x-1) for x in cm)-saving
print(sum(v[2:])-minimum)
