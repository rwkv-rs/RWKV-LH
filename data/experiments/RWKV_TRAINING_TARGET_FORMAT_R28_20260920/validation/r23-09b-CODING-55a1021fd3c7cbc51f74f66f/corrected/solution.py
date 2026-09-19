import sys
v=sys.stdin.read().split();out=[]
for s in v[1:1+int(v[0])]:
 n=len(s);possible=n>=10
 if not possible:
  for i in range(1,n):
   for j in range(i+1,n):
    for k in range(j+1,n):
     if len({s[:i],s[i:j],s[j:k],s[k:]})==4:possible=True
 out.append('YES' if possible else 'NO')
print('\n'.join(out))
