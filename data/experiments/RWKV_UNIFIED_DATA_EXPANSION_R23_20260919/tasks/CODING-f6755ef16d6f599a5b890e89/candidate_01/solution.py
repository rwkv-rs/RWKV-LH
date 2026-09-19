import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
def floor_sum(n,m,a,b):
 answer=0
 while True:
  if a>=m:answer+=(n-1)*n*(a//m)//2;a%=m
  if b>=m:answer+=n*(b//m);b%=m
  top=a*n+b
  if top<m:return answer
  n=top//m;b=top%m;m,a=a,m
for books,people,initial in zip(v,v,v):
 if books==people==initial==0:break
 out.append(str(floor_sum(people,people,books,initial)))
print('\n'.join(out))
