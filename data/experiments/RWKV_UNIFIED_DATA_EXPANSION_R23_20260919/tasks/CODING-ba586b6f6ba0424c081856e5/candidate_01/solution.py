import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];differences=[a[i+1]-a[i] for i in range(n-1)];p=n+1;m=v[p];p+=1;size=1
while size<max(1,n-1):size*=2
length=[1]*(2*size);first=[0]*(2*size);last=[0]*(2*size);prefix=[0]*(2*size);suffix=[0]*(2*size);best=[0]*(2*size)
def merge(i):
 l=2*i;r=l+1;length[i]=length[l]+length[r];first[i]=first[l];last[i]=last[r]
 connect=last[l]!=0 and first[r]!=0 and not(last[l]<0 and first[r]>0)
 prefix[i]=prefix[l];suffix[i]=suffix[r];best[i]=max(best[l],best[r])
 if connect:
  best[i]=max(best[i],suffix[l]+prefix[r])
  if prefix[l]==length[l]:prefix[i]+=prefix[r]
  if suffix[r]==length[r]:suffix[i]+=suffix[l]
for i,d in enumerate(differences):
 j=size+i;first[j]=last[j]=(d>0)-(d<0);prefix[j]=suffix[j]=best[j]=int(d!=0)
for i in range(size-1,0,-1):merge(i)
def change(i,delta):
 differences[i]+=delta;d=differences[i];j=size+i;first[j]=last[j]=(d>0)-(d<0);prefix[j]=suffix[j]=best[j]=int(d!=0);j//=2
 while j:merge(j);j//=2
out=[]
for _ in range(m):
 l,r,d=v[p:p+3];p+=3
 if l>1:change(l-2,d)
 if r<n:change(r-1,-d)
 out.append(str(best[1]+1))
print('\n'.join(out))
