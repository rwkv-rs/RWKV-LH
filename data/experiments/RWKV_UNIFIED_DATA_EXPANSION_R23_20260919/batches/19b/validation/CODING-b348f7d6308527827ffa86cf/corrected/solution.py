import sys
cache={};out=[]
for n in map(int,sys.stdin.read().split()):
 if n not in cache:
  base=10**(n//2);answer=[]
  for root in range(base):
   square=root*root
   if square//base+square%base==root:answer.append(f'{square:0{n}d}')
  cache[n]=answer
 out.extend(cache[n])
print('\n'.join(out))
