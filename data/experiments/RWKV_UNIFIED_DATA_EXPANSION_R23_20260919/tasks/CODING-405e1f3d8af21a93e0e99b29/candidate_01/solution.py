import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];up=[1]*n;down=[0]*n
for i in range(n):
 for j in range(i):
  if a[j]>a[i]:down[i]=max(down[i],up[j]+1)
  elif a[j]<a[i] and down[j]:up[i]=max(up[i],down[j]+1)
print(max(max(up),max(down)))
