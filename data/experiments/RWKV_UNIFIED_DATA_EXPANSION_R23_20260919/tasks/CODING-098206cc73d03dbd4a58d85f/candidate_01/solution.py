import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m,k=v[:3];a=[v[3+i*m:3+(i+1)*m] for i in range(n)]
if n>m:a=list(map(list,zip(*a)));n,m=m,n
answer=0
for top in range(n):
 columns=[0]*m
 for bottom in range(top,n):
  row=a[bottom];frequency={0:1};prefix=0
  for j in range(m):
   columns[j]+=row[j];prefix=(prefix+columns[j])%k;answer+=frequency.get(prefix,0);frequency[prefix]=frequency.get(prefix,0)+1
print(answer)
