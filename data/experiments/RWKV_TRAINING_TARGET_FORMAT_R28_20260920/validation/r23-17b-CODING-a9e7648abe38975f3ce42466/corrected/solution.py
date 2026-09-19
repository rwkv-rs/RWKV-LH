import sys,math
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 a=next(v)**2;b=next(v)**2;c=next(v)**2
 side2=(a+b+c+math.sqrt(max(0,3*(2*(a*b+a*c+b*c)-a*a-b*b-c*c))))/2
 out.append(f'{math.sqrt(3)*side2/4:.2f}')
print('\n'.join(out))
