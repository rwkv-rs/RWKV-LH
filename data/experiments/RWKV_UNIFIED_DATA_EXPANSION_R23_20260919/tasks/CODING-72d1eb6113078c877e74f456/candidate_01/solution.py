import sys,math
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));ops=[];p=1;maximum=1
for _ in range(v[0]):
 kind=v[p];p+=1
 if kind==1:ops.append((1,v[p]));maximum=max(maximum,v[p]);p+=1
 else:ops.append((2,*v[p:p+3]));p+=3
bits=maximum.bit_length();roots=array('i',[0])*(maximum+1);L=array('i',[0]);R=array('i',[0]);minimum=array('i',[10**9]);present=bytearray(maximum+1)
def node():L.append(0);R.append(0);minimum.append(10**9);return len(L)-1
def insert(divisor,value):
 if not roots[divisor]:roots[divisor]=node()
 u=roots[divisor];minimum[u]=min(minimum[u],value)
 for bit in range(bits-1,-1,-1):
  links=R if value>>bit&1 else L
  if not links[u]:links[u]=node()
  u=links[u];minimum[u]=min(minimum[u],value)
out=[]
for op in ops:
 if op[0]==1:
  value=op[1]
  if present[value]:continue
  present[value]=1
  for d in range(1,math.isqrt(value)+1):
   if value%d==0:
    insert(d,value)
    if d*d!=value:insert(value//d,value)
 else:
  _,x,k,s=op;limit=s-x
  if x%k or k>maximum or not roots[k] or minimum[roots[k]]>limit:out.append('-1');continue
  u=roots[k];answer=0
  for bit in range(bits-1,-1,-1):
   desired=1-((x>>bit)&1);w=R[u] if desired else L[u]
   if not w or minimum[w]>limit:desired^=1;w=R[u] if desired else L[u]
   answer|=desired<<bit;u=w
  out.append(str(answer))
print('\n'.join(out))
