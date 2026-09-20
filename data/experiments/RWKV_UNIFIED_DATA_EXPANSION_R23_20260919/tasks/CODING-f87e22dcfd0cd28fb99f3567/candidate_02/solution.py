import sys
P=1000000007
lines=sys.stdin.buffer.readlines();n,k,q=map(int,lines[0].split());A=[[int(c)-48 for c in row.strip()] for row in lines[1:n+1]]
queries=[list(map(int,row.split())) for row in lines[n+1:n+q+1]]
width=9;shift=72*(n-1);mask=(1<<72)-1
# Every dot product is below 60*(P-1)^2 < 2^72, so lanes do not carry.
def pack(row):return int.from_bytes(b''.join(x.to_bytes(9,'little') for x in row),'little')
def dot(a,b):return ((a*b>>shift)&mask)%P
def columns(matrix):return [pack([matrix[j][i] for j in range(n-1,-1,-1)]) for i in range(n)]
def right(row,cols):
 r=pack(row);return [dot(r,c) for c in cols]
def left(rows,col):
 c=pack(col[::-1]);return [dot(r,c) for r in rows]
ac=columns(A);ar=[pack(row) for row in A];B=[row[:] for row in A]
states=[]
for a,s,b,t in queries:
 r=[0]*n;c=[0]*n;r[s-1]=1;c[t-1]=1;states.append([a,b,r,c,0,s==t,s-1,t-1])
for level in range(1,k+1):
 F=[row[:] for row in B]
 for i in range(n):F[i][i]=(F[i][i]+1)%P
 fc=columns(F);fr=[pack(row) for row in F]
 for state in states:
  a,b,r,c,answer,same,s,t=state
  if level>=max(a,b):
   if level==a==b:answer+=same
   elif level==a:answer+=sum(x*y for x,y in zip(A[s],c))
   elif level==b:answer+=sum(r[i]*A[i][t] for i in range(n))
   else:answer+=sum(x*y for x,y in zip(right(r,ac),left(ar,c)))
  state[4]=answer%P
  if level!=a:state[2]=right(r,fc)
  if level!=b:state[3]=left(fr,c)
 if level<k:
  bc=columns(B);br=[pack(row) for row in B]
  B=[[(B[i][j]+dot(br[i],bc[j]))%P for j in range(n)] for i in range(n)]
print('\n'.join(str(state[4]) for state in states))
