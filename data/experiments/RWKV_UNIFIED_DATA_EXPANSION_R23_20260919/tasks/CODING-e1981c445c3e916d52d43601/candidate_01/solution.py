import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n,P,Q=next(it),next(it),next(it);a=sorted(next(it) for _ in range(n));money=P+2*Q;odd=count=spent=0
 for x in a:
  if x%2 and odd==P:continue
  if spent+x>money:break
  spent+=x;odd+=x%2;count+=1
 out.append(str(count))
print('\n'.join(out))
