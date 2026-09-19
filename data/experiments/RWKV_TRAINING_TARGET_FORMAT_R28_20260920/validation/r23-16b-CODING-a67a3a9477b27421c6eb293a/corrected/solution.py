import sys
v=sys.stdin.read().split();s=v[0];k=int(v[1]);a=[p-i for i,p in enumerate(j for j,c in enumerate(s) if c=='Y')];pre=[0]
for x in a:pre.append(pre[-1]+x)
left=0;best=0
for right in range(len(a)):
 while left<=right:
  mid=(left+right)//2;cost=a[mid]*(mid-left)-(pre[mid]-pre[left])+(pre[right+1]-pre[mid+1])-a[mid]*(right-mid)
  if cost<=k:break
  left+=1
 best=max(best,right-left+1)
print(best)
