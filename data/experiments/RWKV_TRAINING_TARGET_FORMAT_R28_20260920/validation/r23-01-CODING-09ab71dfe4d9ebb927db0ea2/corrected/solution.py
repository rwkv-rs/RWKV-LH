import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=sorted([(v[i+1],i+1) for i in range(n)],reverse=True);q=v[n+1];queries=[]
for j in range(q):
 l,r,k=v[n+2+3*j:n+5+3*j];queries.append((k,l,r,j))
queries.sort(reverse=True);bit=[0]*(n+1);ans=[0]*q;pos=0
def pref(x):
 s=0
 while x:s+=bit[x];x-=x&-x
 return s
for k,l,r,j in queries:
 while pos<n and a[pos][0]>k:
  x=a[pos][1]
  while x<=n:bit[x]+=1;x+=x&-x
  pos+=1
 ans[j]=pref(r)-pref(l-1)
print('\n'.join(map(str,ans)))
