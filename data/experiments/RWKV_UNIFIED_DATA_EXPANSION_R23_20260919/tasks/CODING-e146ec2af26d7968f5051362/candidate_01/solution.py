import sys
from decimal import Decimal as D,getcontext,ROUND_HALF_UP
getcontext().prec=50
v=[D(x) for x in sys.stdin.read().split()];p=0;out=[];case=0
while p<len(v) and v[p]!=-1:
 stations=[D(0)]
 while v[p]!=0:stations.append(v[p]*5280);p+=1
 p+=1;speed,acceleration,stop=v[p:p+3];p+=3;legs=[b-a for a,b in zip(stations,stations[1:])];reverse=legs[::-1];total=stations[-1];ramp=speed/acceleration;travel=[d/speed+ramp for d in legs];journey=sum(travel)+(len(legs)-1)*stop
 arrivals_left=[D(0)]
 for time in travel:arrivals_left.append(arrivals_left[-1]+time+stop)
 arrivals_left=[t-stop if i else t for i,t in enumerate(arrivals_left)]
 arrivals_right=[D(0)]
 for time in reversed(travel):arrivals_right.append(arrivals_right[-1]+time+stop)
 arrivals_right=[t-stop if i else t for i,t in enumerate(arrivals_right)][::-1]
 meeting=None;station=None
 for i in range(1,len(stations)-1):
  first=max(arrivals_left[i],arrivals_right[i]);last=min(arrivals_left[i]+stop,arrivals_right[i]+stop)
  if first<=last:meeting=first;station=i;position=stations[i];break
 def displacement(time,route):
  travelled=D(0)
  for d in route:
   duration=d/speed+ramp
   if time<=duration:
    if time<=ramp:return travelled+acceleration*time*time/2
    if time<=d/speed:return travelled+speed*speed/(2*acceleration)+(time-ramp)*speed
    return travelled+d-acceleration*(duration-time)**2/2
   time-=duration;travelled+=d
   if time<=stop:return travelled
   time-=stop
  return travelled
 if meeting is None:
  low=D(0);high=journey
  for _ in range(160):
   mid=(low+high)/2
   if displacement(mid,legs)+displacement(mid,reverse)>=total:high=mid
   else:low=mid
  meeting=(low+high)/2;position=displacement(meeting,legs)
 case+=1;minute=meeting.quantize(D('0.1'),rounding=ROUND_HALF_UP);miles=(position/5280).quantize(D('0.001'),rounding=ROUND_HALF_UP);lines=[f'Scenario #{case}:',f'Meeting time: {minute} minutes',f'Meeting distance: {miles} miles from metro center hub'+(f', in station {station}' if station is not None else '')];out.append('\n'.join(lines))
print('\n\n'.join(out))
