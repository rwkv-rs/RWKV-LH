import sys,math
a,b,n=map(int,sys.stdin.buffer.read().split());B=(n-1).bit_length();rows={};limits={}
for exponent in range(B-1,1,-1):
 lo,hi=1,math.isqrt(n-1)+1
 while lo+1<hi:
  mid=(lo+hi)//2
  if mid**exponent<n:lo=mid
  else:hi=mid
 limit=lo;limits[exponent]=limit;current=bytearray(limit+2);above=rows.get(exponent+1,bytearray(2));above_limit=limits.get(exponent+1,1)
 for x in range(limit,1,-1):current[x]=int((x<limit and not current[x+1]) or (x<=above_limit and not above[x]))
 rows[exponent]=current
root=math.isqrt(n-1);row1=bytearray(root+2);following=int((n-root-2)%2) if root+1<n else 1
for x in range(root,1,-1):
 right_safe=x+1<n;next_win=row1[x+1] if x<root else following;up=rows.get(2,bytearray(root+1));row1[x]=int((right_safe and not next_win) or not up[x])
if a>=2:
 if b==1:win=bool(row1[a]) if a<=root else bool((n-1-a)%2)
 else:win=bool(rows[b][a])
 print('Masha' if win else 'Stas')
else:
 state=0
 for exponent in range(B-1,b-1,-1):
  child=bool(row1[2]) if exponent==1 and root>=2 else (bool((n-3)%2) if exponent==1 else bool(rows[exponent][2]))
  if not child or state==-1:state=1
  elif state==0:state=0
  else:state=-1
 print('Masha' if state==1 else 'Stas' if state==-1 else 'Missing')
