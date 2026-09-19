import sys
v=iter(sys.stdin.read().split());n=int(next(v));points=sorted(set((float(next(v)),float(next(v))) for _ in range(n)))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
hull=[]
for p in points:
 while len(hull)>=2 and cross(hull[-2],hull[-1],p)<=0:hull.pop()
 hull.append(p)
low=len(hull)
for p in reversed(points[:-1]):
 while len(hull)>low and cross(hull[-2],hull[-1],p)<=0:hull.pop()
 hull.append(p)
if len(hull)>1:hull.pop()
h=len(hull);best=0.0
if h>=4:
 a=hull+hull
 for i in range(h):
  left=i+1;right=i+3
  for j in range(i+2,i+h-1):
   if left>=j:left=j-1
   while left+1<j and abs(cross(a[i],a[j],a[left+1]))>=abs(cross(a[i],a[j],a[left])):left+=1
   right=max(right,j+1)
   while right+1<i+h and abs(cross(a[i],a[j],a[right+1]))>=abs(cross(a[i],a[j],a[right])):right+=1
   best=max(best,abs(cross(a[i],a[j],a[left]))+abs(cross(a[i],a[j],a[right])))
elif h==3:
 for p in points:
  if p not in hull:best=max(best,abs(cross(*hull))-min(abs(cross(hull[i],hull[(i+1)%3],p)) for i in range(3)))
print(f'{best/2:.3f}')
