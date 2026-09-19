import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);q=next(it);zero=[0]*(4*n);one=[0]*(4*n);two=[0]*(4*n);lazy=[0]*(4*n)
def build(node,l,r):
 zero[node]=r-l+1
 if l<r:mid=(l+r)//2;build(2*node,l,mid);build(2*node+1,mid+1,r)
def rotate(node,k):
 if k==1:zero[node],one[node],two[node]=two[node],zero[node],one[node]
 elif k==2:zero[node],one[node],two[node]=one[node],two[node],zero[node]
 lazy[node]=(lazy[node]+k)%3
def operation(node,l,r,a,b,update):
 if a<=l and r<=b:
  if update:rotate(node,1);return 0
  return zero[node]
 if lazy[node]:rotate(2*node,lazy[node]);rotate(2*node+1,lazy[node]);lazy[node]=0
 mid=(l+r)//2;answer=0
 if a<=mid:answer+=operation(2*node,l,mid,a,b,update)
 if b>mid:answer+=operation(2*node+1,mid+1,r,a,b,update)
 if update:zero[node]=zero[2*node]+zero[2*node+1];one[node]=one[2*node]+one[2*node+1];two[node]=two[2*node]+two[2*node+1]
 return answer
build(1,0,n-1);out=[]
for _ in range(q):
 kind=next(it);a=next(it);b=next(it);answer=operation(1,0,n-1,a,b,kind==0)
 if kind==1:out.append(str(answer))
print('\n'.join(out))
