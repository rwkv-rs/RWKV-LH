import sys
v=iter(sys.stdin.read().split());n=int(next(v));s=next(v);q=int(next(v));cache={};out=[]
for _ in range(q):
 budget=int(next(v));c=next(v);key=(budget,c)
 if key not in cache:
  left=wrong=best=0
  for right,ch in enumerate(s):
   wrong+=ch!=c
   while wrong>budget:wrong-=s[left]!=c;left+=1
   best=max(best,right-left+1)
  cache[key]=best
 out.append(str(cache[key]))
print('\n'.join(out))
