import sys
n=int(sys.stdin.buffer.read());states={(0,None):1,(1,1):1};mod=998244353
for height in range(2,n.bit_length()+1):
 new={}
 for (left,lp),lc in states.items():
  root=(left+1)%2
  if left and lp==root:continue
  for (right,rp),rc in states.items():
   if right and rp!=0:continue
   key=(left+right+1,root);new[key]=(new.get(key,0)+lc*rc)%mod
 states=new
print(sum(count for (size,parity),count in states.items() if size==n)%mod)
