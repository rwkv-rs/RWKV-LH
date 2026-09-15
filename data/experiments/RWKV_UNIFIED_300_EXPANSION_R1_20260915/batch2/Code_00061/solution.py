import sys,bisect
a=list(map(int,sys.stdin.buffer.read().split()));n,m=a[:2];a=sorted(a[2:]);pref=[0]
for v in a:pref.append(pref[-1]+v)
lo,hi=0,2*a[-1]+1
while hi-lo>1:
    mid=(lo+hi)//2;count=sum(n-bisect.bisect_left(a,mid-v) for v in a)
    if count>=m:lo=mid
    else:hi=mid
count=total=0
for v in a:
    i=bisect.bisect_left(a,lo-v);count+=n-i;total+=(n-i)*v+pref[-1]-pref[i]
print(total-(count-m)*lo)
