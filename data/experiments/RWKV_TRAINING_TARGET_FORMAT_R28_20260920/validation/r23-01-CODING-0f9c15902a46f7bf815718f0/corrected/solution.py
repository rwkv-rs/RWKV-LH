import sys,math,bisect
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];limit=math.isqrt(max(a));g=bytearray(limit+1);freq=[0]*64;left=1;right=0
for x in range(2,limit+1):
 hi=math.isqrt(x);lo=math.isqrt(hi)
 if lo**4<x:lo+=1
 while right<hi:right+=1;freq[g[right]]+=1
 while left<lo:freq[g[left]]-=1;left+=1
 mex=0
 while freq[mex]:mex+=1
 g[x]=mex
positions=[[] for _ in range(max(g)+1)]
for x,value in enumerate(g):positions[value].append(x)
answer=0
for x in a:
 if x<=limit:value=g[x]
 else:
  hi=math.isqrt(x);lo=math.isqrt(hi)
  if lo**4<x:lo+=1
  value=0
  while value<len(positions):
   p=positions[value];i=bisect.bisect_left(p,lo)
   if i==len(p) or p[i]>hi:break
   value+=1
 answer^=value
print('Furlo' if answer else 'Rublo')
