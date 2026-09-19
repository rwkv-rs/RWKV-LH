import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));n,m,k=v[:3];a=v[3:];residue=0;modulus=1
for i,value in enumerate(a):
 g=math.gcd(modulus,value);difference=-i-residue
 if difference%g:print('NO');raise SystemExit
 quotient=value//g;step=(difference//g*pow(modulus//g,-1,quotient))%quotient if quotient>1 else 0;residue+=modulus*step;modulus*=quotient;residue%=modulus
 if modulus>n:print('NO');raise SystemExit
start=residue or modulus
print('YES' if start+k-1<=m and all(math.gcd(modulus,start+i)==x for i,x in enumerate(a)) else 'NO')
