import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=sorted(v[1:n+1]);b=sorted(v[n+1:]);lo=left=0;hi=right=n-1;score=0
while lo<=hi:
 if a[hi]>b[right]:score+=100;hi-=1;right-=1
 elif a[lo]>b[left]:score+=100;lo+=1;left+=1
 else:
  if a[lo]==b[right]:score+=50
  lo+=1;right-=1
print(score)
