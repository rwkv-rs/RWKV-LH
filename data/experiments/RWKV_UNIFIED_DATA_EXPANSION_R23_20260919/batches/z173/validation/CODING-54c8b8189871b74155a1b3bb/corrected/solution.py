import sys,re
P=10**9
lines=sys.stdin.buffer.read().split();n=int(lines[0]);x=list(map(int,lines[1:n+1]));expr=b''.join(lines[n+1:]).decode();tokens=re.findall(r'[0-9]+|X|N|\*:|\+/|[-+*()]',expr);moments=[n];powers=[1]*n

def multiply(a,b):
 if isinstance(a,int) and isinstance(b,int):return a*b%P
 if isinstance(a,int):return [a*y%P for y in b]
 if isinstance(b,int):return [b*y%P for y in a]
 c=[0]*(len(a)+len(b)-1)
 for i,u in enumerate(a):
  for j,v in enumerate(b):c[i+j]+=u*v
 return [u%P for u in c]
def add(a,b,sign):
 if isinstance(a,int) and isinstance(b,int):return (a+sign*b)%P
 if isinstance(a,int):a=[a]
 if isinstance(b,int):b=[b]
 c=a[:]+[0]*max(0,len(b)-len(a))
 for i,u in enumerate(b):c[i]=(c[i]+sign*u)%P
 return c
values=[];operators=[]
def apply(op):
 a=values.pop()
 if op=='neg':values.append((-a)%P if isinstance(a,int) else [(-u)%P for u in a])
 elif op=='*:':values.append(multiply(a,a))
 elif op=='+/':
  while len(moments)<len(a):
   for i,u in enumerate(x):powers[i]=powers[i]*u%P
   moments.append(sum(powers)%P)
  values.append(sum(u*v for u,v in zip(a,moments))%P)
 else:
  b=values.pop();values.append(multiply(b,a) if op=='*' else add(b,a,1 if op=='+' else -1))
expect_term=True
for token in tokens:
 if token=='(':
  operators.append(token);expect_term=True
 elif token==')':
  while operators[-1]!='(':apply(operators.pop())
  operators.pop();expect_term=False
 elif token in ('+','-','*','*:','+/'):
  operators.append('neg' if token=='-' and expect_term else token);expect_term=True
 else:
  values.append([0,1] if token=='X' else n if token=='N' else int(token)%P);expect_term=False
while operators:apply(operators.pop())
print(values[0]%P)
