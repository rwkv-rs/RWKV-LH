import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 s,n=next(it),next(it);a=[next(it) for _ in range(n)];last={};diff=[0]*(s+1);constraints=0
 for j,x in enumerate(a):
  if x in last and j-last[x]<s:
   i=last[x];l=(i+1)%s;r=j%s;constraints+=1
   if l<=r:diff[l]+=1;diff[r+1]-=1
   else:diff[l]+=1;diff[s]-=1;diff[0]+=1;diff[r+1]-=1
  last[x]=j
 value=answer=0
 for r in range(s):value+=diff[r];answer+=(value==constraints)
 out.append(str(answer))
print('\n'.join(out))
