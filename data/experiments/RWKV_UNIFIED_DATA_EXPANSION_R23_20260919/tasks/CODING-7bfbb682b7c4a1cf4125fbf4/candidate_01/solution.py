import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 h,w=next(it),next(it);g=math.gcd(h,w);h//=g;w//=g
 if h%2==0 or w%2==0:out.append('1 1')
 else:out.append(str((h*w+1)//2)+' '+str((h*w-1)//2))
print('\n'.join(out))
