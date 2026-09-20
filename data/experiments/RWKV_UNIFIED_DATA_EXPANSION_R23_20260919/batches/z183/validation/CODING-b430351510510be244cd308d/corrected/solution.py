import sys
from fractions import Fraction

def solve(length,A,B):
 faces=[(axis,side) for axis in range(3) for side in (0,length[axis])];starts=[i for i,(a,v) in enumerate(faces) if A[a]==v];ends={i for i,(a,v) in enumerate(faces) if B[a]==v}
 if set(starts)&ends:return sum((a-b)**2 for a,b in zip(A,B))
 best=10**30
 def point(origin,basis,coordinates):return tuple(origin[j]+sum(basis[i][j]*coordinates[i] for i in range(3)) for j in range(2))
 def crosses(P,Q,hinges):
  delta=(Q[0]-P[0],Q[1]-P[1]);last=Fraction(0)
  for U,V in hinges:
   axis=0 if U[0]==V[0] else 1;other=1-axis;low=min(U[other],V[other]);high=max(U[other],V[other])
   if delta[axis]:
    t=Fraction(U[axis]-P[axis],delta[axis])
    if t<last or t>1:return False
    value=P[other]+t*delta[other]
    if value<low or value>high:return False
    last=t
   else:
    if P[axis]!=U[axis]:return False
    if not delta[other]:
     if not low<=P[other]<=high:return False
    else:
     a=Fraction(low-P[other],delta[other]);b=Fraction(high-P[other],delta[other]);lo=min(a,b);hi=max(a,b);last=max(last,lo)
     if last>hi or last>1:return False
  return True
 def visit(face,origin,basis,used,hinges,P):
  nonlocal best
  if face in ends:
   Q=point(origin,basis,B);distance=sum((x-y)**2 for x,y in zip(P,Q))
   if distance<best and crosses(P,Q,hinges):best=distance
  axis,side=faces[face]
  for nxt,(b,edge) in enumerate(faces):
   if b==axis or used>>nxt&1:continue
   c=3-axis-b;shared=[0,0,0];shared[axis]=side;shared[b]=edge;U=point(origin,basis,shared);shared[c]=length[c];V=point(origin,basis,shared);sa=1 if side==0 else -1;sb=1 if edge==0 else -1;new=[(0,0)]*3;new[axis]=tuple(-sa*sb*x for x in basis[b]);new[c]=basis[c];base=tuple(U[j]-new[axis][j]*side for j in range(2));visit(nxt,base,new,used|(1<<nxt),hinges+[(U,V)],P)
 for face in starts:
  a,_=faces[face];free=[i for i in range(3) if i!=a];basis=[(0,0)]*3;basis[free[0]]=(1,0);basis[free[1]]=(0,1);P=point((0,0),basis,A);visit(face,(0,0),basis,1<<face,[],P)
 return best
v=list(map(int,sys.stdin.buffer.read().split()));output=[]
for i in range(0,len(v),9):output.append(str(solve(v[i:i+3],v[i+3:i+6],v[i+6:i+9])))
print('\n'.join(output))
