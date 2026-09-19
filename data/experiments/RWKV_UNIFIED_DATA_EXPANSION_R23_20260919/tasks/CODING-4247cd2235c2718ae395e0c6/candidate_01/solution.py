import sys,heapq
from collections import defaultdict
v=list(map(int,sys.stdin.buffer.read().split()));events=defaultdict(list)
for i in range(0,len(v),3):
 l,h,r=v[i:i+3];events[l].append((-h,r));events[r]
heap=[(0,float('inf'))];last=0;out=[]
for x in sorted(events):
 for event in events[x]:heapq.heappush(heap,event)
 while heap[0][1]<=x:heapq.heappop(heap)
 height=-heap[0][0]
 if height!=last:out.extend((str(x),str(height)));last=height
print(' '.join(out))
