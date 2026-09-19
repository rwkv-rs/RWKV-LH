import sys
out=[]
for n in map(int,sys.stdin.buffer.read().split()):
 if n==0:break
 lo=0;hi=1<<((n.bit_length()+5)//6)
 while lo<hi:
  mid=(lo+hi)//2
  if mid**6<n:lo=mid+1
  else:hi=mid
 out.append('Special' if lo**6==n else 'Ordinary')
print('\n'.join(out))
