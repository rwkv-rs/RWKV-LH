import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=v[1:];mod=1000000007;dp=[1]
for i in range(1,n):
 prefix=[0]
 for x in dp:prefix.append((prefix[-1]+x)%mod)
 total=prefix[-1]
 if a[i-1]>a[i]:dp=prefix
 elif a[i-1]<a[i]:dp=[(total-x)%mod for x in prefix]
 else:dp=[total]*(i+1)
print(sum(dp)%mod)
