import sys,math
a=list(map(int,sys.stdin.buffer.read().split()));n,m,k=a[:3];prefix=[0]*(n+1)
for i,x in enumerate(a[3:3+n],1):prefix[i]=prefix[i-1]^x
block=max(1,int(n/max(1,math.sqrt(m))));queries=[]
for i in range(m):
 l,r=a[3+n+2*i:5+n+2*i];l-=1;b=l//block;queries.append((b,r if b%2==0 else -r,l,r,i))
queries.sort();freq=[0]*(1<<20);left=0;right=-1;total=0;answers=[0]*m
for _,__,l,r,index in queries:
 while right<r:
  right+=1;x=prefix[right];total+=freq[x^k];freq[x]+=1
 while left>l:
  left-=1;x=prefix[left];total+=freq[x^k];freq[x]+=1
 while right>r:
  x=prefix[right];freq[x]-=1;total-=freq[x^k];right-=1
 while left<l:
  x=prefix[left];freq[x]-=1;total-=freq[x^k];left+=1
 answers[index]=total
print('\n'.join(map(str,answers)))
