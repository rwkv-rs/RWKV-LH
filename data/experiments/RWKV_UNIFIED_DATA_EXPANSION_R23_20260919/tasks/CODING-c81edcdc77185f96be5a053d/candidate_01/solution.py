import sys
v=iter(sys.stdin.buffer.read().split());out=[]
def evaluate(a,x):
 value=0.0
 for c in a:value=value*x+c
 return value
def roots(a):
 n=len(a)-1
 if n==1:return [-a[1]/a[0]]
 critical=roots([a[i]*(n-i) for i in range(n)]);points=[-26.0]+critical+[26.0];answer=[]
 for l,r in zip(points,points[1:]):
  fl=evaluate(a,l);fr=evaluate(a,r)
  if fl*fr>0:continue
  for _ in range(90):
   mid=(l+r)/2;fm=evaluate(a,mid)
   if fl*fm<=0:r=mid
   else:l=mid;fl=fm
  answer.append((l+r)/2)
 return answer
for token in v:
 n=int(token)
 if not n:break
 a=[float(next(v)) for _ in range(n+1)];z=roots(a);out.append(f'Equation {len(out)+1}: '+' '.join(f'{0.0 if abs(x)<0.00005 else x:.4f}' for x in z))
print('\n'.join(out))
