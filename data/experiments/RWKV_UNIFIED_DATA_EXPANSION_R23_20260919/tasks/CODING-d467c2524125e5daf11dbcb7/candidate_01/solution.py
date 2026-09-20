import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);a=[next(it) for _ in range(n)];q=next(it);queries=[next(it)-1 for _ in range(q)];position=[0]*(n+1)
for i,v in enumerate(a):position[v]=i
size=1<<(n-1).bit_length();counts=[0]*(2*size);sums=[0]*(2*size);lazy=[0]*(2*size)
def insert(node,lo,hi,p):
 if lo==hi:counts[node]=1;sums[node]=0;lazy[node]=0;return 0
 left=node*2;right=left+1
 if lazy[node]:
  z=lazy[node];lazy[left]+=z;lazy[right]+=z;sums[left]+=z*counts[left];sums[right]+=z*counts[right];lazy[node]=0
 mid=(lo+hi)//2
 if p<=mid:answer=sums[right]+insert(left,lo,mid,p)
 else:sums[left]+=counts[left];lazy[left]+=1;answer=insert(right,mid+1,hi,p)
 counts[node]=counts[left]+counts[right];sums[node]=sums[left]+sums[right];return answer
triples=0
for value in range(n,0,-1):triples+=insert(1,0,size-1,position[value])
del counts,sums,lazy,position
BLOCK=32;prefix=[0];bits=0
for i,value in enumerate(a,1):
 bits|=1<<value
 if i%BLOCK==0:prefix.append(bits)
out=[]
for i in queries:
 x=a[i];y=a[i+1];high=max(x,y);low=min(x,y);block=i//BLOCK;left=block*BLOCK;smaller=(prefix[block]&((1<<high)-1)).bit_count()
 for j in range(left,i):smaller+=a[j]<high
 delta=smaller-(high-low-1);triples += delta if x<y else -delta
 if (i+1)%BLOCK==0:prefix[(i+1)//BLOCK]^=(1<<x)|(1<<y)
 a[i],a[i+1]=y,x;out.append('Yes' if triples==0 else 'No')
print('\n'.join(out))
