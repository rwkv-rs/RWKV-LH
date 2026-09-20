import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n,q=v[:2];a=v[2:2+n];queries=v[2+n:];prefix=[0];parity=[0,0];alternate=[0]*(n+1)
for i,x in enumerate(a):prefix.append(prefix[-1]+x);parity[i%2]+=x;alternate[i+1]=parity[i%2]
out=[]
for x in queries:
 low,high=0,n//2
 while low<high:
  k=(low+high+1)//2;j=n-k
  if a[j]>=x and j-bisect.bisect_left(a,2*x-a[j],0,j)>=k:low=k
  else:high=k-1
 k=low;answer=prefix[n]-prefix[n-k]
 if not k:out.append(str(alternate[n]));continue
 l,r=0,n-k
 while l<r:
  mid=(l+r)//2
  if x-a[mid]>a[mid+k]-x:l=mid+1
  else:r=mid
 end=l+k-1
 if end==n-k-1:answer+=alternate[l]
 else:answer+=a[n-k-1]+(alternate[l-1] if l else 0)
 out.append(str(answer))
print('\n'.join(out))
