import sys,math,bisect,heapq
v=iter(sys.stdin.buffer.read().split());output=[]
for token in v:
 n=int(token);T=int(next(v));radius=int(next(v))
 if n==T==radius==0:break
 names=[];routes=[];ends=[]
 for _ in range(n):
  names.append(next(v).decode());start=int(next(v));x=int(next(v));y=int(next(v));segments=[]
  while start<T:
   end=int(next(v));vx=int(next(v));vy=int(next(v));segments.append((start,end,x,y,vx,vy));x+=(end-start)*vx;y+=(end-start)*vy;start=end
  routes.append(segments);ends.append([row[1] for row in segments])
 def contact(a,b,time):
  ra=routes[a];rb=routes[b];i=min(bisect.bisect_right(ends[a],time),len(ra)-1);j=min(bisect.bisect_right(ends[b],time),len(rb)-1)
  while i<len(ra) and j<len(rb):
   sa,ea,xa,ya,vxa,vya=ra[i];sb,eb,xb,yb,vxb,vyb=rb[j];lo=max(time,sa,sb);hi=min(ea,eb)
   if lo>hi:return math.inf
   x=xa+(lo-sa)*vxa-xb-(lo-sb)*vxb;y=ya+(lo-sa)*vya-yb-(lo-sb)*vyb;vx=vxa-vxb;vy=vya-vyb;C=x*x+y*y-radius*radius
   if C<=0:return lo
   A=vx*vx+vy*vy;B=2*(x*vx+y*vy)
   if A and B<0:
    disc=B*B-4*A*C
    if disc>=0:
     delay=2*C/(-B+math.sqrt(disc));arrival=lo+delay
     if arrival<=hi+1e-10:return min(arrival,hi)
   if ea<=eb:i+=1
   if eb<=ea:j+=1
  return math.inf
 distance=[math.inf]*n;distance[0]=0.;queue=[(0.,0)];done=[False]*n
 while queue:
  time,u=heapq.heappop(queue)
  if done[u]:continue
  done[u]=True
  for w in range(n):
   if not done[w]:
    arrival=contact(u,w,time)
    if arrival<distance[w]:distance[w]=arrival;heapq.heappush(queue,(arrival,w))
 output.extend(sorted(names[i] for i in range(n) if distance[i]<=T))
print('\n'.join(output))
