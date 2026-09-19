import sys
a=list(map(int,sys.stdin.buffer.read().split()));n,k=a[:2];key=[-1]*256;out=[]
for x in a[2:2+n]:
 if key[x]<0:
  lo=max(0,x-k+1);j=x
  while j>=lo and key[j]<0:j-=1
  if j<lo:start=lo
  elif x-key[j]<k:start=key[j]
  else:start=j+1
  for v in range(start,x+1):
   if key[v]<0:key[v]=start
 out.append(str(key[x]))
print(' '.join(out))
