import sys
from array import array
stream=sys.stdin.buffer;n=int(stream.readline());a=[]
while len(a)<n:
 row=list(map(int,stream.readline().split()))
 if row:a.append(row)
rank=[]
for row in a:
 r=array('H',[0])*n
 for k,j in enumerate(sorted(range(n),key=row.__getitem__)):r[j]=k
 rank.append(r)
answer=0;last=n-1
for j in range(n):
 for c,i in enumerate(sorted(range(n),key=lambda i:a[i][j])):
  r=rank[i][j];answer+=r*(last-c)+(last-r)*c
print(answer//2)
