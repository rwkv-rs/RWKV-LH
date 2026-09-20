import sys,math
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
v=iter(sys.stdin.buffer.read().split());n=int(next(v));f=int(next(v));points=[tuple(float(next(v)) for _ in range(3)) for _ in range(n)];faces=[[int(next(v))-1 for _ in range(int(next(v)))] for _ in range(f)];volume=0.;moment=[0.,0.,0.]
for face in faces:
 a=points[face[0]]
 for j in range(1,len(face)-1):
  b=points[face[j]];c=points[face[j+1]];six=dot(a,cross(b,c));volume+=six
  for d in range(3):moment[d]+=six*(a[d]+b[d]+c[d])/4
center=[x/volume for x in moment];relative=[tuple(p[d]-center[d] for d in range(3)) for p in points];norms=[math.sqrt(dot(p,p)) for p in relative];out=[]
for face in faces:
 area=0.;i=face[0];a=relative[i];na=norms[i]
 for j,k in zip(face[1:],face[2:]):
  b=relative[j];c=relative[k];nb=norms[j];nc=norms[k];numerator=abs(dot(a,cross(b,c)));denominator=na*nb*nc+dot(a,b)*nc+dot(b,c)*na+dot(c,a)*nb;area+=2*math.atan2(numerator,denominator)
 out.append(f'{area/(4*math.pi):.7f}')
print('\n'.join(out))
