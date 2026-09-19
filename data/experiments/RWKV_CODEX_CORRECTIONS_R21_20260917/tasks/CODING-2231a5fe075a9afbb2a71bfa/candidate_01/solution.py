import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];reach=1;mask=(1<<k)-1;A=B=0
for i in range(n):
 a,b=v[2+2*i:4+2*i];A+=a;B+=b
 lo=max(0,k-b);hi=min(k,a)
 if lo<=hi:
  bits=reach;width=hi-lo+1;span=1
  while span<width:
   step=min(span,width-span)%k
   bits|=((bits<<step)|(bits>>(k-step)))&mask
   span+=min(span,width-span)
  shift=lo%k;reach|=((bits<<shift)|(bits>>(k-shift)))&mask
ans=(A+B)//k
for r in range(k):
 if (reach>>r)&1 and (A-r)%k+(B+r)%k<k:print(ans);break
else:print(ans-1)
