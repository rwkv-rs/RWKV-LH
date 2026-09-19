import sys
s=sorted(sys.stdin.read().strip(),reverse=True);n=len(s);best=0
for mask in range(1,(1<<n)-1):
 a=b=0
 for i,c in enumerate(s):
  if mask>>i&1:a=10*a+int(c)
  else:b=10*b+int(c)
 if a and b:best=max(best,a*b)
print(best)
