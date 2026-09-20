import sys,functools
it=iter(sys.stdin.read().split());out=[]
for case in range(1,int(next(it))+1):
 n=int(next(it));cells=next(it)+next(it);N=2*n;limit=1<<N;colors={}
 for i,c in enumerate(cells):colors[c]=colors.get(c,0)|(1<<i)
 rectangles=[]
 for l in range(n):
  for r in range(l,n):
   mask=((1<<(r-l+1))-1)<<l;rectangles.extend((mask,mask<<n,mask|(mask<<n)))
 rectangles.sort(key=int.bit_count,reverse=True);mono=bytearray(limit);mono[0]=1
 for mask in range(1,limit):bit=mask&-mask;i=bit.bit_length()-1;mono[mask]=int(mask&~colors[cells[i]]==0)
 @functools.lru_cache(None)
 def solve(mask):
  if not mask:return 0
  if mono[mask]:return 1
  answer=mask.bit_count();seen=set()
  for rectangle in rectangles:
   removed=mask&rectangle
   if removed and mono[removed]:
    remaining=mask^removed
    if remaining in seen:continue
    seen.add(remaining);answer=min(answer,1+solve(remaining))
    if answer==2:break
  return answer
 out.append(f'Case #{case}: {solve(limit-1)}')
print('\n'.join(out))
