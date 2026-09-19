import sys,math
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);counts={}
 for i in range(n):
  x=next(v);new=counts.copy();new[x]=new.get(x,0)+1
  for g,c in counts.items():h=math.gcd(g,x);new[h]=new.get(h,0)+c
  counts=new
 out.append(str(counts.get(1,0)))
print('\n'.join(out))
