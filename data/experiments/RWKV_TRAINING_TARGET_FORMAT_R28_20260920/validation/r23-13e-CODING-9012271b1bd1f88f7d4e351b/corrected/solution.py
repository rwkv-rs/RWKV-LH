import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];s=v[1:];bit=[0]*(n+1)
for i in range(1,n+1):left=i-(i&-i);bit[i]=i*(i+1)//2-left*(left+1)//2
answer=[0]*n
for i in range(n-1,-1,-1):
 target=s[i];index=0;step=1<<(n.bit_length()-1)
 while step:
  candidate=index+step
  if candidate<=n and bit[candidate]<=target:target-=bit[candidate];index=candidate
  step//=2
 value=index+1;answer[i]=value;j=value
 while j<=n:bit[j]-=value;j+=j&-j
print(' '.join(map(str,answer)))
