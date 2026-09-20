import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=[0]*n
for x,y in zip(v[1::2],v[2::2]):a[x]=y
low=[];small=n
for y in a:small=min(small,y);low.append(small)
high=[0]*n;large=-1
for i in range(n-1,-1,-1):large=max(large,a[i]);high[i]=large
count=[0]*(n+1);first=[0]*(n+1);second=[0]*(n+1);answer=0
for l,u in zip(low,high):
 p=l+1
 while p<=n:count[p]+=1;first[p]+=l;second[p]+=l*l;p+=p&-p
 c=s=q=0;p=u+1
 while p:c+=count[p];s+=first[p];q+=second[p];p-=p&-p
 answer+=((u+1)*(u+2)*c-(2*u+3)*s+q)//2
print(answer%1000000007)
