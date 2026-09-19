import sys
it=iter(sys.stdin.buffer.read().split());t=int(next(it));out=[]
for _ in range(t):
 s=next(it);last=0;best=1
 for i,c in enumerate(s,1):
  if c==82:
   best=max(best,i-last);last=i
 out.append(str(max(best,len(s)+1-last)))
print('\n'.join(out))
