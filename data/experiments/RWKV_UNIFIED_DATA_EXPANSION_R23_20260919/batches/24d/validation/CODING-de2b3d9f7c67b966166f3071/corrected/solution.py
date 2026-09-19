import sys
out=[]
for n in map(int,sys.stdin.read().split()):
 bound=1;stan=True
 while bound<n:
  bound*=9 if stan else 2
  if bound>=n:break
  stan=not stan
 out.append('Stan wins.' if stan else 'Ollie wins.')
print('\n'.join(out))
