import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);prefix=0;minimum=0;min_count=1;best=None;count=0
 for i in range(n):
  prefix+=next(v);value=prefix-minimum
  if best is None or value>best:best=value;count=min_count
  elif value==best:count+=min_count
  if prefix<minimum:minimum=prefix;min_count=1
  elif prefix==minimum:min_count+=1
 out.append(str(best)+' '+str(count))
print('\n'.join(out))
