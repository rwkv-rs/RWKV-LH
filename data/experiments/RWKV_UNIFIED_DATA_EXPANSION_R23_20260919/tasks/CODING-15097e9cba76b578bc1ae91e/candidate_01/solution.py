import sys
v=sys.stdin.buffer.read().split();tables=[]
for digit in range(16):
 bit=1<<(digit%4);position=digit//4
 for limit,sign in ((digit,1),(digit-1,-1)):
  if limit<0:continue
  allowed=[x for x in range(limit+1) if x&bit];count=len(allowed)
  if not count:continue
  powers=[1]
  for _ in range(15):powers.append(powers[-1]*(limit+1))
  less=[sum(x<y for x in allowed) for y in range(16)];tables.append((position,limit,sign,bit,count,powers,less))
def prefix(n):
 if n<0:return 0
 digits=[int(c,16) for c in format(n,'015x')];answer=0
 for position,limit,sign,bit,count,powers,less in tables:
  total=0
  for index,x in enumerate(digits):
   remaining=14-index
   options=less[x] if remaining==position else min(x,limit+1)
   suffix=count*powers[remaining-1] if remaining>position else powers[remaining]
   total+=options*suffix
   if x>limit or (remaining==position and not x&bit):break
  else:total+=1
  answer+=sign*total
 return answer
out=[]
for i in range(int(v[0])):
 l,r=int(v[1+2*i],16),int(v[2+2*i],16);out.append(str(prefix(r)-prefix(l-1)))
print('\n'.join(out))
