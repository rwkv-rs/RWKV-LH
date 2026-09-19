import sys
it=iter(map(int,sys.stdin.buffer.read().split()));r=next(it);c=next(it);n=next(it);points=[]
def boundary(x,y):
 if x==0:return y
 if y==c:return c+x
 if x==r:return c+r+c-y
 if y==0:return 2*c+2*r-x
 return None
for i in range(n):
 a=boundary(next(it),next(it));b=boundary(next(it),next(it))
 if a is not None and b is not None:points.extend(((a,i),(b,i)))
stack=[]
for position,i in sorted(points):
 if stack and stack[-1]==i:stack.pop()
 else:stack.append(i)
print('NO' if stack else 'YES')
