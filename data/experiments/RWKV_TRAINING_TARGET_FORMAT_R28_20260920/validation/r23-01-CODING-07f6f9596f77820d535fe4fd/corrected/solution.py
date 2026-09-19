import sys
out=[]
for n in map(int,sys.stdin.buffer.read().split()):
 if n==0:break
 ans=0;l=1
 while l<=n:
  q=n//l;r=n//q;ans+=q*(l+r)*(r-l+1)//2;l=r+1
 out.append(str(ans-1))
print('\n'.join(out))
