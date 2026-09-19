import sys
v=iter(sys.stdin.read().split());n=int(next(v));m=int(next(v));s=next(v);tree=[[0]*10 for _ in range(4*n)];lazy=[0]*(4*n)
def build(p,l,r):
 if l==r:tree[p][int(s[l])]=1;return
 mid=(l+r)//2;build(p*2,l,mid);build(p*2+1,mid+1,r);tree[p]=[a+b for a,b in zip(tree[p*2],tree[p*2+1])]
def rotate(p,k):
 k%=10
 if k:tree[p]=tree[p][-k:]+tree[p][:-k];lazy[p]=(lazy[p]+k)%10
def update(p,l,r,a,b):
 if a<=l and r<=b:
  answer=sum(i*c for i,c in enumerate(tree[p]));rotate(p,1);return answer
 if lazy[p]:rotate(p*2,lazy[p]);rotate(p*2+1,lazy[p]);lazy[p]=0
 mid=(l+r)//2;answer=0
 if a<=mid:answer+=update(p*2,l,mid,a,b)
 if b>mid:answer+=update(p*2+1,mid+1,r,a,b)
 tree[p]=[x+y for x,y in zip(tree[p*2],tree[p*2+1])];return answer
build(1,0,n-1);out=[]
for _ in range(m):out.append(str(update(1,0,n-1,int(next(v))-1,int(next(v))-1)))
print('\n'.join(out))
