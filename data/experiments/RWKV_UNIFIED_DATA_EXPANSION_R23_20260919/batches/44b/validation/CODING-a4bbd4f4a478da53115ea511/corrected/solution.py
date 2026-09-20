import sys
v=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(v),next(v);count=[0]*(4*n+8);lazy=bytearray(4*n+8)
def flip(node,l,r,a,b):
 if a<=l and r<=b:count[node]=r-l+1-count[node];lazy[node]^=1;return
 mid=(l+r)//2;left=node*2;right=left+1
 if lazy[node]:count[left]=mid-l+1-count[left];count[right]=r-mid-count[right];lazy[left]^=1;lazy[right]^=1;lazy[node]=0
 if a<=mid:flip(left,l,mid,a,b)
 if b>mid:flip(right,mid+1,r,a,b)
 count[node]=count[left]+count[right]
def query(node,l,r,a,b,inherited=False):
 if a<=l and r<=b:return r-l+1-count[node] if inherited else count[node]
 inherited^=bool(lazy[node]);mid=(l+r)//2;answer=0
 if a<=mid:answer+=query(node*2,l,mid,a,b,inherited)
 if b>mid:answer+=query(node*2+1,mid+1,r,a,b,inherited)
 return answer
out=[]
for _ in range(m):
 kind,a,b=next(v),next(v),next(v)
 if a>b:a,b=b,a
 if kind==0:flip(1,1,n,a,b)
 else:out.append(str(query(1,1,n,a,b)))
print('\n'.join(out))
