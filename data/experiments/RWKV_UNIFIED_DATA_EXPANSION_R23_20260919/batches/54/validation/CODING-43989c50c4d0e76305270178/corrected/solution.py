import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for case in range(1,next(it)+1):
 W,H=next(it),next(it);limit=min(W,H)//2;answer=0
 for r in range(1,limit+1):
  for s in range(r,limit+1):
   distance=r+s;subtotal=0
   for dx in range(distance+1):
    dy=math.isqrt(distance*distance-dx*dx)
    if dx*dx+dy*dy!=distance*distance:continue
    nx=max(0,min(W-r,W-s-dx)-max(r,s-dx)+1);ny=max(0,min(H-r,H-s-dy)-max(r,s-dy)+1);subtotal+=nx*ny*(2 if dx else 1)*(2 if dy else 1)
   answer+=subtotal//2 if r==s else subtotal
 out.append(f'Case {case}: {answer}')
print('\n'.join(out))
