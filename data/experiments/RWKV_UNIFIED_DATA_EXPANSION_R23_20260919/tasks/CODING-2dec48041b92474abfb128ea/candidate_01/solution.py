import sys
v=sys.stdin.buffer.read().split();n,x=map(int,v[:2]);pattern=v[2];MOD=1000000007;width=n+1
def letter(c):
 a=[[0]*(i+1) for i in range(width)]
 for i in range(width):a[i][i]=2 if i in (0,n) else 1
 for i in range(1,width):
  if pattern[i-1]==c:a[i][i-1]=1
 return a
def multiply(a,b):
 out=[]
 for i in range(width):
  row=[0]*(i+1)
  for k,value in enumerate(a[i]):
   if value:
    for j,other in enumerate(b[k]):row[j]+=value*other
  out.append([value%MOD for value in row])
 return out
previous=letter(48);current=letter(49)
if x==0:print(previous[n][0])
else:
 for _ in range(2,x+1):previous,current=current,multiply(previous,current)
 print(current[n][0])
