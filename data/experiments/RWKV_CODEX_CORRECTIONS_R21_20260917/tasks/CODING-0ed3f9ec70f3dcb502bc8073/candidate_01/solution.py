import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 s=next(it);n=next(it);last={};diff=[0]*(s+1)
 for q in range(n):
  song=next(it);p=last.get(song);last[song]=q
  if p is not None and q-p<s:
   left=(q+1)%s;right=p%s
   if left<=right:diff[left]+=1;diff[right+1]-=1
   else:diff[left]+=1;diff[s]-=1;diff[0]+=1;diff[right+1]-=1
 total=answer=0
 for i in range(s):total+=diff[i];answer+=total==0
 out.append(str(answer))
print('\n'.join(out))
