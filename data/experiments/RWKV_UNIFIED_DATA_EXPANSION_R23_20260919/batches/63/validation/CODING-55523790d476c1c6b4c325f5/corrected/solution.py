import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];q=v[n+1];queries=[[] for _ in range(n)]
for i in range(q):l,r=v[n+2+2*i:n+4+2*i];queries[r-1].append((l-1,i))
INF=10**12;minimum=[INF]*(4*n);count=[0]*(4*n);history=[0]*(4*n);lazy=[0]*(4*n);ticks=[0]*(4*n)
def build(p,l,r):
 count[p]=r-l+1
 if l<r:mid=(l+r)//2;build(p*2,l,mid);build(p*2+1,mid+1,r)
def tick(p,value):history[p]+=count[p]*value;ticks[p]+=value
def push(p):
 for child in (p*2,p*2+1):minimum[child]+=lazy[p];lazy[child]+=lazy[p]
 lazy[p]=0
 if ticks[p]:
  for child in (p*2,p*2+1):
   if minimum[child]==minimum[p]:tick(child,ticks[p])
  ticks[p]=0
def add(p,l,r,ql,qr,value):
 if ql<=l and r<=qr:minimum[p]+=value;lazy[p]+=value;return
 push(p);mid=(l+r)//2
 if ql<=mid:add(p*2,l,mid,ql,qr,value)
 if qr>mid:add(p*2+1,mid+1,r,ql,qr,value)
 minimum[p]=min(minimum[p*2],minimum[p*2+1]);count[p]=(count[p*2] if minimum[p*2]==minimum[p] else 0)+(count[p*2+1] if minimum[p*2+1]==minimum[p] else 0);history[p]=history[p*2]+history[p*2+1]
def query(p,l,r,start):
 if start<=l:return history[p]
 push(p);mid=(l+r)//2;answer=query(p*2+1,mid+1,r,start)
 if start<=mid:answer+=query(p*2,l,mid,start)
 return answer
build(1,0,n-1);maxima=[];minima=[];out=[0]*q
for r,x in enumerate(a):
 if r:add(1,0,n-1,0,r-1,-1)
 while maxima and a[maxima[-1]]<x:
  old=maxima.pop();left=maxima[-1]+1 if maxima else 0;add(1,0,n-1,left,old,x-a[old])
 while minima and a[minima[-1]]>x:
  old=minima.pop();left=minima[-1]+1 if minima else 0;add(1,0,n-1,left,old,a[old]-x)
 maxima.append(r);minima.append(r);add(1,0,n-1,r,r,-INF);tick(1,1)
 for l,i in queries[r]:out[i]=query(1,0,n-1,l)
print('\n'.join(map(str,out)))
