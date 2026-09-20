import sys
MOD=1000000007
v=iter(sys.stdin.buffer.read().split());tests=int(next(v));answers=[]
for _ in range(tests):
 n=int(next(v));m=int(next(v));grid=[next(v) for _ in range(n)];cells=b''.join(grid);unknown=[i for i,c in enumerate(cells) if c==46];k=len(unknown);size=n*m;dest=[-1]*size
 for j,i in enumerate(unknown):dest[i]=j
 def step(i,c):
  row,col=divmod(i,m)
  if c==76:return i-1 if col else -1
  if c==82:return i+1 if col+1<m else -1
  if c==85:return i-m if row else -1
  return i+m if row+1<n else -1
 valid=True
 for start in range(size):
  if dest[start]!=-1:continue
  path=[];u=start
  while u>=0 and dest[u]==-1:
   dest[u]=-2;path.append(u);u=step(u,cells[u])
  if u>=0 and dest[u]==-2:valid=False;break
  target=k if u<0 else dest[u]
  for i in path:dest[i]=target
 if not valid:answers.append('0');continue
 matrix=[[0]*k for _ in range(k)]
 for i,pos in enumerate(unknown):
  for direction in b'LRUD':
   neighbor=step(pos,direction);target=k if neighbor<0 else dest[neighbor]
   if target==i:continue
   matrix[i][i]+=1
   if target<k:matrix[i][target]-=1
 determinant=1
 for col in range(k):
  pivot=next((r for r in range(col,k) if matrix[r][col]%MOD),None)
  if pivot is None:determinant=0;break
  if pivot!=col:matrix[pivot],matrix[col]=matrix[col],matrix[pivot];determinant=-determinant
  row=matrix[col];value=row[col]%MOD;determinant=determinant*value%MOD;inv=pow(value,MOD-2,MOD)
  for r in range(col+1,k):
   current=matrix[r];factor=current[col]*inv%MOD
   if factor:
    for j in range(col+1,k):current[j]=(current[j]-factor*row[j])%MOD
   current[col]=0
 answers.append(str(determinant%MOD))
print('\n'.join(answers))
