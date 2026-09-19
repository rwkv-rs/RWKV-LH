import sys,bisect
lines=iter(sys.stdin.read().splitlines());out=[];case=0
for line in lines:
 if not line.strip():continue
 n=int(line)
 if n==0:break
 sections=[];distance=0
 for _ in range(n):
  p=next(lines).split()
  if p[2]=='road':sections.append((0,int(p[3]),[]));distance+=int(p[3])
  else:sections.append((1,int(p[3])*60,[int(x)*60 for x in p[5:]]))
 def arrival(speed):
  t=0.0
  for typ,value,depart in sections:
   if typ==0:t+=value*3600/speed
   else:
    hour=int(t//3600);j=bisect.bisect_left(depart,t-hour*3600-1e-7)
    if j==len(depart):hour+=1;j=0
    t=hour*3600+depart[j]+value
  return t
 end=round(arrival(80));lo=0.0;hi=80.0
 if distance:
  for _ in range(70):
   mid=(lo+hi)/2
   if arrival(mid)<=end+1e-7:hi=mid
   else:lo=mid
 else:hi=0.0
 case+=1;h,rem=divmod(end,3600);m,s=divmod(rem,60);out.append(f'Test Case {case}: {h:02d}:{m:02d}:{s:02d} {hi:.2f}')
print('\n\n'.join(out)+'\n')
