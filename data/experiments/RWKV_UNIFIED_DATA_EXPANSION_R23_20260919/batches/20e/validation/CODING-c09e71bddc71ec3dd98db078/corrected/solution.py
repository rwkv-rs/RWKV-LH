import sys
v=iter(map(int,sys.stdin.read().split()));blocks=[]
while True:
 n=next(v)
 if n==0:break
 out=[]
 while True:
  first=next(v)
  if first==0:break
  order=[first]+[next(v) for _ in range(n-1)];stack=[];current=1;ok=True
  for x in order:
   while current<=n and (not stack or stack[-1]!=x):stack.append(current);current+=1
   if stack and stack[-1]==x:stack.pop()
   else:ok=False;break
  out.append('Yes' if ok else 'No')
 blocks.append('\n'.join(out))
print('\n\n'.join(blocks))
