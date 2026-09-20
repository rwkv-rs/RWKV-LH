import sys,heapq
stream=sys.stdin;n,m,K=map(int,stream.readline().split());names=[];index={};failures=[];accepted=[];pending=[];solved=[];penalty=[]
for _ in range(K):
 clock,problem,name,verdict=stream.readline().rstrip('\n').split(' ',3);h,minute,second=map(int,clock.split(':'));seconds=h*3600+minute*60+second;p=ord(problem)-65
 if name not in index:
  index[name]=len(names);names.append(name);failures.append([0]*n);accepted.append([False]*n);pending.append([None]*n);solved.append(0);penalty.append(0)
 i=index[name]
 if accepted[i][p]:continue
 if verdict=='Accepted':
  accepted[i][p]=True;value=seconds//60+20*failures[i][p]
  if seconds<=14400:solved[i]+=1;penalty[i]+=value
  else:pending[i][p]=value
 else:failures[i][p]+=1
heap=[(solved[i],-penalty[i],-i) for i in range(len(names))];heapq.heapify(heap);next_problem=[0]*len(names);output=[]
while heap:
 _,_,negative=heapq.heappop(heap);i=-negative;output.append(names[i]);p=next_problem[i]
 while p<n:
  value=pending[i][p];p+=1
  if value is None:continue
  solved[i]+=1;penalty[i]+=value;key=(solved[i],-penalty[i],-i)
  if heap and key>heap[0]:heapq.heappush(heap,key);break
 next_problem[i]=p
print('\n'.join(output))
