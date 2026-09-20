import sys,bisect
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);prefix=[0];zeros=[0];positions=[[] for _ in range(9)];positions[0].append(0)
for i in range(1,n+1):
 x=next(it);prefix.append(prefix[-1]+x);zeros.append(zeros[-1]+(x==0));positions[prefix[-1]%9].append(i)
out=[]
for _ in range(next(it)):
 l,r=next(it),next(it);first=[-1]*9;last=[-1]*9;possible={0} if zeros[r]>zeros[l-1] else set()
 for a in range(9):
  p=positions[a];i=bisect.bisect_left(p,l-1);j=bisect.bisect_right(p,r)-1
  if i<=j:first[a]=p[i];last[a]=p[j]
 for a in range(9):
  if first[a]<0:continue
  for b in range(9):
   if last[b]>first[a] and prefix[last[b]]>prefix[first[a]]:possible.add((b-a-1)%9+1)
 answer=sorted(possible,reverse=True)[:5];answer+=[-1]*(5-len(answer));out.append(' '.join(map(str,answer)))
print('\n'.join(out))
