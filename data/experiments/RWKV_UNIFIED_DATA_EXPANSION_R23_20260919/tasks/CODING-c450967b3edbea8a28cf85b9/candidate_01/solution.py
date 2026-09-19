import sys
n,k=map(int,sys.stdin.read().split())
def count(y):
 l=y;r=y+(2 if y%2==0 else 1);answer=0
 while l<=n:answer+=max(0,min(n+1,r)-l);l*=2;r*=2
 return answer
answer=1
for parity in (0,1):
 lo=0 if parity else 1;hi=(n-parity)//2+1
 while lo<hi:
  mid=(lo+hi)//2;y=2*mid+parity
  if y>=1 and count(y)>=k:lo=mid+1
  else:hi=mid
 candidate=2*(lo-1)+parity
 if candidate>=1 and count(candidate)>=k:answer=max(answer,candidate)
print(answer)
