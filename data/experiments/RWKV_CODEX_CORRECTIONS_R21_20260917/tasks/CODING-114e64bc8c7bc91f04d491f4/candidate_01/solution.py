import sys
from functools import lru_cache
l,r=map(int,sys.stdin.buffer.read().split())
def count(bound):
 if bound<10**10:return 0
 digits=list(map(int,str(bound)))
 @lru_cache(None)
 def visit(pos,last,run,found,mask,tight):
  if pos==11:return int(found)
  total=0;upper=digits[pos] if tight else 9
  for d in range(1 if pos==0 else 0,upper+1):
   m=mask|(1 if d==4 else 2 if d==8 else 0)
   if m==3:continue
   length=min(3,run+1) if d==last else 1;total+=visit(pos+1,d,length,found or length==3,m,tight and d==upper)
  return total
 return visit(0,-1,0,False,0,True)
print(count(r)-count(l-1))
