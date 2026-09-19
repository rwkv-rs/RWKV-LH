import sys
v=sys.stdin.read().split();n=int(v[0]);s=v[1];t=v[2];l=0;r=n-1
while s[l]==t[l]:l+=1
while s[r]==t[r]:r-=1
print(int(s[l+1:r+1]==t[l:r])+int(t[l+1:r+1]==s[l:r]))
