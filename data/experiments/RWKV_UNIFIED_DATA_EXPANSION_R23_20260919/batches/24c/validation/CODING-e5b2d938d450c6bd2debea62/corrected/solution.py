import sys
v=list(map(int,sys.stdin.read().split()));n,w=v[:2];bit=[0]*602;out=[]
for count,score in enumerate(v[2:2+n],1):
 p=score+1
 while p<602:bit[p]+=1;p+=p&-p
 rank=count-max(1,count*w//100)+1;index=0;step=512
 while step:
  j=index+step
  if j<602 and bit[j]<rank:rank-=bit[j];index=j
  step//=2
 out.append(str(index))
print(' '.join(out))
