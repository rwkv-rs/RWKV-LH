import sys
v=sys.stdin.read().split();out=[]
for s in v[1:1+int(v[0])]:
 n=len(s);prefix=[0]*(n+1)
 for i,c in enumerate(s):prefix[i+1]=prefix[i]^(1<<int(c))
 answer=None
 for i in range(n-1,-1,-1):
  for digit in range(int(s[i])-1,-1,-1):
   if i==0 and digit==0:continue
   mask=prefix[i]^(1<<digit);remaining=n-i-1;odd=mask.bit_count()
   if odd>remaining or (remaining-odd)%2:continue
   suffix='9'*(remaining-odd)+''.join(str(d) for d in range(9,-1,-1) if mask>>d&1);answer=s[:i]+str(digit)+suffix;break
  if answer is not None:break
 out.append(answer if answer is not None else '9'*(n-2))
print('\n'.join(out))
