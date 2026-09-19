import sys,bisect
v=iter(map(int,sys.stdin.read().split()));out=[]
def groups(a):
 result=[[] for _ in range(len(a)+1)];result[0]=[0]
 for count,x in enumerate(a):
  for k in range(count+1,0,-1):result[k].extend(s+x for s in result[k-1])
 return result
for _ in range(next(v)):
 n=next(v);a=[next(v) for i in range(n)];left=groups(a[:n//2]);right=groups(a[n//2:]);total=sum(a);count=n//2;best=total
 for x in right:x.sort()
 for k,values in enumerate(left):
  if not 0<=count-k<len(right):continue
  other=right[count-k]
  for s in values:
   p=bisect.bisect_left(other,(total-2*s+1)//2)
   for q in (p-1,p):
    if 0<=q<len(other):best=min(best,abs(total-2*(s+other[q])))
 out.append(str(best))
print('\n'.join(out))
