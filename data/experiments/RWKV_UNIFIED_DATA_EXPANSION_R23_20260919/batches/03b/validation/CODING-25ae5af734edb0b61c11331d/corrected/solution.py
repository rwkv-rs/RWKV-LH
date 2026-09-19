import sys,math
a,b=map(int,sys.stdin.buffer.read().split());found=set()
for start in range(1,math.isqrt(b)+1):
 total=start*start;end=start+1
 while total+end*end<=b:
  total+=end*end;end+=1
  if total>=a and str(total)==str(total)[::-1]:found.add(total)
print(sum(found))
