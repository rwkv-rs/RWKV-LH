import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];a=v[2:2+n]
for height in v[2+n:2+n+m]:
 eaten=0
 for i in range(n):
  if a[i]>eaten:
   top=min(a[i],height);a[i]+=top-eaten;eaten=top
   if eaten==height:break
print('\n'.join(map(str,a)))
