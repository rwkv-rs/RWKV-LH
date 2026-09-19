import sys
v=list(map(int,sys.stdin.read().split()));out=[]
for n in v[1:1+v[0]]:
 digits=[]
 while n:digits.append(n%3);n//=3
 digits.append(0)
 for i in range(len(digits)-1):
  if digits[i]>=2:
   digits[i]=0;digits[i+1]+=1
   for j in range(i):digits[j]=0
 out.append(str(sum(d*3**i for i,d in enumerate(digits))))
print('\n'.join(out))
