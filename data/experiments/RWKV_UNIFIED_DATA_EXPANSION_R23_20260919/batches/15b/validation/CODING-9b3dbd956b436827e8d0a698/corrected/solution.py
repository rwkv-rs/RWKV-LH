import sys
v=list(map(int,sys.stdin.read().split()));n,q=v[:2];out=[]
for x in v[2:2+q]:
 while x%2==0:x=n+x//2
 out.append(str((x+1)//2))
print('\n'.join(out))
