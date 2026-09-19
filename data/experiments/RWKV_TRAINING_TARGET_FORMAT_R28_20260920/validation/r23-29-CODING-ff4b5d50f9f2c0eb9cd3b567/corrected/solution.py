import sys
v=sys.stdin.read().split();out=[]
for s in v[1:1+int(v[0])]:
 ok=int(s)%4==0
 for left in range(len(s)):
  for right in range(left+1,len(s)+1):
   remaining=s[:left]+s[right:]
   if remaining and int(remaining)>0 and int(remaining)%4==0:ok=True
 out.append('Yes' if ok else 'No')
print('\n'.join(out))
