import sys
def solve(n,intervals):
 mask=(1<<(n+1))-1;dp=[(1,0)];previous=0
 def spread(bits,length):
  step=1
  while length:
   take=min(step,length);bits=(bits|(bits<<take))&mask;length-=take;step*=2
  return bits
 for left,right in intervals:
  gap=left-previous;length=right-left;new=[[0,0] for _ in range(len(dp)+2)]
  for j,(a,b) in enumerate(dp):
   b=(b<<gap)&mask
   new[j][0]|=a;new[j][1]|=(b<<length)&mask
   sa=spread(a,length) if a else 0;sb=spread(b,length) if b else 0
   new[j+1][1]|=sa;new[j+1][0]|=sb
   new[j+2][0]|=sa;new[j+2][1]|=sb
  dp=new;previous=right
 gap=2*n-previous
 for j,(a,b) in enumerate(dp):
  if ((a|((b<<gap)&mask))>>n)&1:return j
 return None
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);k=next(v);result=solve(n,[(next(v),next(v)) for _ in range(k)])
if result is None:print('Hungry')
else:print('Full');print(result)
