import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);m=int(v[1]);mask=sum(1<<(4*i) for i in range(m));basis=[None]*m;rank=0

def add(a,b):
 s=a+b;reduce=((s>>3)|((s>>2)&((s>>1)|s)))&mask;return s-5*reduce

def encode(word):
 value=0
 for i,ch in enumerate(word):value|=(ch-97)<<(4*i)
 return value
for word in v[2:n+2]:
 value=encode(word)
 while value:
  pivot=((value&-value).bit_length()-1)//4;digit=(value>>(4*pivot))&15
  if basis[pivot] is None:
   twice=add(value,value);multiples=[0,value,twice,add(twice,value),add(twice,twice)];value=multiples[(0,1,3,2,4)[digit]];twice=add(value,value);basis[pivot]=[0,add(twice,twice),add(twice,value),twice,value];rank+=1;break
  value=add(value,basis[pivot][digit])
ways=pow(5,n-rank,1000000007);q=int(v[n+2]);out=[]
for word in v[n+3:n+3+q]:
 value=encode(word)
 while value:
  pivot=((value&-value).bit_length()-1)//4;digit=(value>>(4*pivot))&15
  if basis[pivot] is None:break
  value=add(value,basis[pivot][digit])
 out.append(str(ways if value==0 else 0))
print('\n'.join(out))
