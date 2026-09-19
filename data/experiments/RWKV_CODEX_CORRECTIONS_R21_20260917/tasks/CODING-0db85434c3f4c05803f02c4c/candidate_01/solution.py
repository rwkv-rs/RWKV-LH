import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,q=v[:2];a=v[2:2+n];queries=[]
for i in range(q):
 threshold,low,high=v[2+n+3*i:5+n+3*i];queries.append((threshold,low,high,i))
queries.sort(reverse=True);order=sorted(range(n),key=a.__getitem__,reverse=True);parent=list(range(n));size=[1]*n;active=[False]*n;bc=[0]*(n+1);bs=[0]*(n+1);bq=[0]*(n+1);tc=ts=tq=0
def change(length,delta):
 global tc,ts,tq
 tc+=delta;ts+=delta*length;tq+=delta*length*length;i=length
 while i<=n:bc[i]+=delta;bs[i]+=delta*length;bq[i]+=delta*length*length;i+=i&-i
def root(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
def count(low):
 if low>n:return 0
 low=max(1,low);c=tc;s=ts;sq=tq;i=low-1
 while i:c-=bc[i];s-=bs[i];sq-=bq[i];i-=i&-i
 return (sq+(3-2*low)*s+(low-1)*(low-2)*c)//2
pos=0;ans=[0]*q
for threshold,low,high,j in queries:
 while pos<n and a[order[pos]]>=threshold:
  x=order[pos];pos+=1;active[x]=True;change(1,1)
  for y in (x-1,x+1):
   if 0<=y<n and active[y]:
    r=root(x);s=root(y)
    if r!=s:
     change(size[r],-1);change(size[s],-1)
     if size[r]<size[s]:r,s=s,r
     parent[s]=r;size[r]+=size[s];change(size[r],1)
 ans[j]=count(low)-count(high+1)
print('\n'.join(map(str,ans)))
