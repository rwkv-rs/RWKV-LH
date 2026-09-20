import sys,heapq
v=iter(sys.stdin.buffer.read().split());tests=int(next(v));out=[]
for _ in range(tests):
 s=int(next(v));n=int(next(v));parts=[];widths=[];owner=[];starts=[];ends=[];columns=0
 for i in range(s):
  w=int(next(v));widths.append(w);starts.append(columns);ends.append(columns+w-1);owner.extend([i]*w);columns+=w;parts.append([next(v) for _ in range(n)])
 heights=[0]*columns;answer=0
 for rownum in range(n):
  row=b''.join(part[rownum] for part in parts)
  for j,c in enumerate(row):heights[j]=heights[j]+1 if c==48 else 0
  order=sorted((j for j,h in enumerate(heights) if h),key=heights.__getitem__,reverse=True);parent=[-1]*columns;length=[1]*columns;lo=list(range(columns));hi=lo[:];prefix=[0]*s;suffix=[0]*s;full=[False]*s;ph=[];sh=[];fullwidth=0;longest=0;at=0
  def find(x):
   while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
   return x
  def join(a,b):
   a=find(a);b=find(b)
   if a==b:return a
   if length[a]<length[b]:a,b=b,a
   parent[b]=a;length[a]+=length[b];lo[a]=min(lo[a],lo[b]);hi[a]=max(hi[a],hi[b]);return a
  def top_two(heap,current):
   while heap and (full[heap[0][1]] or -heap[0][0]!=current[heap[0][1]]):heapq.heappop(heap)
   if not heap:return [(0,-1)]
   first=heapq.heappop(heap)
   while heap and (full[heap[0][1]] or -heap[0][0]!=current[heap[0][1]] or heap[0][1]==first[1]):heapq.heappop(heap)
   result=[(-first[0],first[1]),(0,-1)]
   if heap:result.append((-heap[0][0],heap[0][1]))
   heapq.heappush(heap,first);return result
  while at<len(order):
   height=heights[order[at]]
   while at<len(order) and heights[order[at]]==height:
    j=order[at];at+=1;piece=owner[j];parent[j]=j;root=j
    if j>starts[piece] and parent[j-1]>=0:root=join(root,j-1)
    if j<ends[piece] and parent[j+1]>=0:root=join(root,j+1)
    longest=max(longest,length[root])
    if lo[root]==starts[piece] and hi[root]==ends[piece]:
     if not full[piece]:full[piece]=True;fullwidth+=widths[piece]
    else:
     if lo[root]==starts[piece]:prefix[piece]=length[root];heapq.heappush(ph,(-length[root],piece))
     if hi[root]==ends[piece]:suffix[piece]=length[root];heapq.heappush(sh,(-length[root],piece))
   width=max(longest,fullwidth)
   for left,i in top_two(sh,suffix):
    for right,j in top_two(ph,prefix):
     if i<0 or j<0 or i!=j:width=max(width,fullwidth+left+right)
   answer=max(answer,height*width)
 out.append(str(answer))
print('\n'.join(out))
