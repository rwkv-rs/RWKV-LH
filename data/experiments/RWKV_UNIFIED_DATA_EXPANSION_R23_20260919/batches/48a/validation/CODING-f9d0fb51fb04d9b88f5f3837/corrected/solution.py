import sys
from functools import lru_cache
v=list(map(int,sys.stdin.buffer.read().split()));a=[];count=[]
for c in v[1:]:
 if a and a[-1]==c:count[-1]+=1
 else:a.append(c);count.append(1)
@lru_cache(None)
def clear(l,r,extra):
 if l>r:return True
 if count[l]+extra>=2 and clear(l+1,r,0):return True
 for j in range(l+1,r+1):
  if a[j]==a[l] and clear(l+1,j-1,0) and clear(j,r,1):return True
 return False
print('yes' if clear(0,len(a)-1,0) else 'no')
