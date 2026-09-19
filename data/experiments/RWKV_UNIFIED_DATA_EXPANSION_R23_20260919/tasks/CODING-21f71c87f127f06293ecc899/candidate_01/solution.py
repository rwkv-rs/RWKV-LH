import sys
out=[];case=0
for n in map(int,sys.stdin.buffer.read().split()):
 if n==0:break
 x=n;parts=[];p=2
 while p*p<=x:
  if x%p==0:
   power=1
   while x%p==0:x//=p;power*=p
   parts.append(power)
  p=3 if p==2 else p+2
 if x>1:parts.append(x)
 answer=sum(parts)+(2-len(parts) if len(parts)<2 else 0);case+=1;out.append(f'Case {case}: {answer}')
print('\n'.join(out))
