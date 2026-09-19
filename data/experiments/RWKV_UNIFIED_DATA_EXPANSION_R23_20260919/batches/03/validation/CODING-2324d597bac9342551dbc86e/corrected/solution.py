import sys
v=sys.stdin.read().split();out=[]
for text in v[1:1+int(v[0])]:
 n=int(text);seen=set();steps=0
 while n!=1 and n not in seen:
  seen.add(n);n=sum(int(c)**2 for c in str(n));steps+=1
 out.append(str(steps if n==1 else -1))
print('\n'.join(out))
