import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];counts=[0]*(n+1)
for x in v[2:]:counts[x]+=1
def complete():
 states={(0,0,0)}
 for i in range(1,n+1):
  new=set()
  for a,b,pair in states:
   rem=counts[i]-a-b
   if rem<0:continue
   new.add((b,rem%3,pair))
   if not pair and rem>=2:new.add((b,(rem-2)%3,1))
  states=new
  if not states:return False
 return (0,0,1) in states
out=[]
for x in range(1,n+1):
 counts[x]+=1
 if complete():out.append(x)
 counts[x]-=1
print(' '.join(map(str,out)) if out else 'NO')
