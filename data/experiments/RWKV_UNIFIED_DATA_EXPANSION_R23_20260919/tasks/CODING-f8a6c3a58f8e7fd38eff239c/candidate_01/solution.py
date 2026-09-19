import sys
w,h,a,b=map(int,sys.stdin.read().split());best=10**9
for x,y in ((a,b),(b,a)):
 if x>w or y>h:continue
 count=0
 while x<w:x*=2;count+=1
 while y<h:y*=2;count+=1
 best=min(best,count)
print(best if best<10**9 else -1)
