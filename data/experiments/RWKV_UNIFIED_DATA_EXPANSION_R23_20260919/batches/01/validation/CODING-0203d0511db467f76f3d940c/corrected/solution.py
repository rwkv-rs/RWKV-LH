import sys
h,w=map(int,sys.stdin.buffer.read().split());P=998244353;size=1<<h;M=[[0]*size for _ in range(size)]
for incoming in range(size):
 def fill(i,out):
  if i==h:M[incoming][out]+=1;return
  if incoming>>i&1:fill(i+1,out);return
  fill(i+1,out);fill(i+1,out|(1<<i))
  if i+1<h and not(incoming>>(i+1)&1):fill(i+2,out)
 fill(0,0)
def mul(a,b):
 cols=list(zip(*b));return [[sum(x*y for x,y in zip(row,col))%P for col in cols] for row in a]
v=[[1]+[0]*(size-1)]
while w:
 if w&1:v=mul(v,M)
 w>>=1
 if w:M=mul(M,M)
print(v[0][0])
