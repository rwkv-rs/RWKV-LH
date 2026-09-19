import sys
v=sys.stdin.read().split();out=[]
for i in range(int(v[0])):
 a=int(v[1+2*i]);n=int(v[2+2*i]);win=(n%2==1) if a%2 else ((n%(a+1))%2==1 or n%(a+1)==a)
 out.append('lsq Win' if win else 'wzt Win')
print('\n'.join(out))
