import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m,p,k=v[:4];template=[v[4+i*p:4+(i+1)*p] for i in range(3)];mask=(1<<m)-1;modmask=(1<<32)-1
horizontal=[j-k for j in range(p) if j!=k and template[1][j]];down=[j-k for j in range(p) if template[2][j]];up=[j-k for j in range(p) if template[0][j]]
def shifted(row,offset):return (row<<offset)&mask if offset>=0 else row>>(-offset)
valid=[row for row in range(1<<m) if all(not(row&shifted(row,d)) for d in horizontal)];size=len(valid);matrix=[[0]*size for _ in range(size)]
for i,a in enumerate(valid):
 for j,b in enumerate(valid):
  if all(not(b&shifted(a,d)) for d in down) and all(not(a&shifted(b,d)) for d in up):matrix[i][j]=1
vector=[1]*size
def multiply(a,b):
 result=[[0]*size for _ in range(size)]
 for i,row in enumerate(a):
  output=result[i]
  for k,value in enumerate(row):
   if value:
    other=b[k]
    for j in range(size):output[j]+=value*other[j]
  for j in range(size):output[j]&=modmask
 return result
power=n-1
while power:
 if power&1:vector=[sum(vector[i]*matrix[i][j] for i in range(size))&modmask for j in range(size)]
 power>>=1
 if power:matrix=multiply(matrix,matrix)
print(sum(vector)&modmask)
