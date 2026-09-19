import sys
s=sys.stdin.read().strip();answer=0;n=len(s)
for left in range(n):
 low=high=0
 for right in range(left,n):
  c=s[right]
  if c=='(':low+=1;high+=1
  elif c==')':low-=1;high-=1
  else:low-=1;high+=1
  if high<0:break
  if low<0:low=(right-left+1)&1
  if low==0:answer+=1
print(answer)
