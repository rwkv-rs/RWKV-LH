import sys
v=sys.stdin.buffer.read().split();t=int(v[0]);queries=[];answers=[0]*t;byballs={};maxneed=0;maxballs=0;maxwickets=0
for i in range(t):
 over,score,target=v[1+3*i:4+3*i];whole,part=map(int,over.split(b'.'));runs,lost=map(int,score.split(b'/'));need=int(target)-runs;balls=120-6*whole-part;wickets=10-lost
 if need<=0:answers[i]=10000
 elif balls>0 and wickets>0:
  byballs.setdefault(balls,[]).append((i,wickets,need));maxneed=max(maxneed,need);maxballs=max(maxballs,balls);maxwickets=max(maxwickets,wickets)
powers=[10**i for i in range(maxballs+maxneed+1)];previous=[[0]*(maxneed+1) for _ in range(maxwickets+1)]
for row in previous:row[0]=1
for balls in range(1,maxballs+1):
 current=[[0]*(maxneed+1) for _ in range(maxwickets+1)]
 for row in current:row[0]=powers[balls]
 for wickets in range(1,maxwickets+1):
  row=current[wickets];same=previous[wickets];lost=previous[wickets-1]
  for need in range(1,maxneed+1):
   value=same[need]+lost[need]+2*row[need-1]
   for runs in range(1,min(6,need-1)+1):value+=powers[runs]*same[need-runs]
   if need<=6:value+=(7-need)*powers[balls+need-1]
   row[need]=value
 for i,wickets,need in byballs.get(balls,[]):answers[i]=current[wickets][need]*10000//powers[balls+need]
 previous=current
for answer in answers:print(f'{answer//100}.{answer%100:02d}')
