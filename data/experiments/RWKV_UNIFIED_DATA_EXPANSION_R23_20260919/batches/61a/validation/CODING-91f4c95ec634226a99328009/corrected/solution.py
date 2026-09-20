import sys
n,m=map(int,sys.stdin.buffer.read().split());P=30011;acc=[[0]*n for _ in range(2)];acc[0][0]=1;sequence=[int(n==1)]
for t in range(1,4*n+20):
 v=acc[(t-1)%2];new=[(v[i]+(v[i-1] if i else 0)+(v[i+1] if i+1<n else 0))%P for i in range(n)];sequence.append(new[-1]);target=acc[t%2]
 for i in range(n):target[i]=(target[i]+new[i])%P
C=[1];B=[1];L=0;shift=1;last=1
for index,value in enumerate(sequence):
 delta=(value+sum(C[j]*sequence[index-j] for j in range(1,L+1)))%P
 if not delta:shift+=1;continue
 old=C[:];factor=delta*pow(last,P-2,P)%P
 if len(C)<len(B)+shift:C += [0]*(len(B)+shift-len(C))
 for j,x in enumerate(B):C[j+shift]=(C[j+shift]-factor*x)%P
 if 2*L<=index:L=index+1-L;B=old;last=delta;shift=1
 else:shift+=1
rec=[-x%P for x in C[1:L+1]]
def multiply(a,b):
 product=[0]*(2*L-1)
 for i,x in enumerate(a):
  for j,y in enumerate(b):product[i+j]=(product[i+j]+x*y)%P
 for i in range(2*L-2,L-1,-1):
  x=product[i]
  for j in range(1,L+1):product[i-j]=(product[i-j]+x*rec[j-1])%P
 return product[:L]
target=m-1
if target<len(sequence):print(sequence[target]);raise SystemExit
if not L:print(0);raise SystemExit
answer=[1]+[0]*(L-1);power=([0,1]+[0]*(L-2)) if L>1 else [rec[0]]
while target:
 if target&1:answer=multiply(answer,power)
 power=multiply(power,power);target//=2
print(sum(x*y for x,y in zip(answer,sequence))%P)
