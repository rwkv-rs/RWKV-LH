import sys
s=sys.stdin.read().strip();mod=1000000007
if 'm' in s or 'w' in s:print(0)
else:
 previous=current=1
 for i,c in enumerate(s):
  value=current
  if i and c in 'un' and s[i-1]==c:value=(value+previous)%mod
  previous,current=current,value
 print(current)
