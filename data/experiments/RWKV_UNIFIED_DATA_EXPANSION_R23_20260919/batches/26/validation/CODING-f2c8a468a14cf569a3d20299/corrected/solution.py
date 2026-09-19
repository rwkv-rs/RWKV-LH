import sys,math
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);m=next(v);a=next(v);d=next(v);divisors=[a+i*d for i in range(5)];answer=m-n+1
 for mask in range(1,32):
  multiple=1
  for i in range(5):
   if mask>>i&1:multiple=math.lcm(multiple,divisors[i])
  count=m//multiple-(n-1)//multiple;answer+=count if mask.bit_count()%2==0 else -count
 out.append(str(answer))
print('\n'.join(out))
