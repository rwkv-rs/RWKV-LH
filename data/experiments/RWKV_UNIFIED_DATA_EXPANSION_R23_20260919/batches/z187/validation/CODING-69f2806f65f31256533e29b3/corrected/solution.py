import sys,heapq
from collections import deque
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);books={1:{},2:{}};heaps={1:[],2:[]};output=[]
for _ in range(n):
 ident=next(v);kind=next(v);limit=next(v);volume=next(v);tip=next(v);opposite=3-kind;book=books[opposite];heap=heaps[opposite];trades={}
 def trade(order,amount):
  if amount:
   key=(ident,order[0]) if kind==1 else (order[0],ident);old=trades.get(key);trades[key]=(order[2],amount+(old[1] if old else 0))
 while volume and heap:
  price=heap[0] if opposite==2 else -heap[0]
  if price not in book:heapq.heappop(heap);continue
  if (kind==1 and price>limit) or (kind==2 and price<limit):break
  queue=book[price];total=sum(order[3] for order in queue)
  if volume>=total:
   for order in queue:trade(order,order[3])
   volume-=total;del book[price];heapq.heappop(heap);continue
  low=0;high=max((order[3]-order[5]+order[4]-1)//order[4]+1 for order in queue)
  while low<high:
   mid=(low+high+1)//2;needed=sum(min(order[3],order[5]+(mid-1)*order[4]) for order in queue)
   if needed<=volume:low=mid
   else:high=mid-1
  if low:
   remaining=deque()
   for order in queue:
    amount=min(order[3],order[5]+(low-1)*order[4]);trade(order,amount);volume-=amount;order[3]-=amount
    if order[3]:order[5]=min(order[3],order[4]);remaining.append(order)
   queue=remaining;book[price]=queue
  while volume:
   order=queue.popleft();amount=min(volume,order[5]);trade(order,amount);volume-=amount;order[3]-=amount;order[5]-=amount
   if order[3]:
    if order[5]:queue.appendleft(order)
    else:order[5]=min(order[3],order[4]);queue.append(order)
  if not queue:del book[price];heapq.heappop(heap)
 for (buy,sell),(price,amount) in sorted(trades.items()):output.append(f'{buy} {sell} {price} {amount}')
 if volume:
  book=books[kind]
  if limit not in book:book[limit]=deque();heapq.heappush(heaps[kind],limit if kind==2 else -limit)
  book[limit].append([ident,kind,limit,volume,tip,min(volume,tip)])
output.append('')
for price in sorted(set(books[1])|set(books[2])):
 for kind in (1,2):
  for order in books[kind].get(price,()):output.append(' '.join(map(str,order)))
print('\n'.join(output))
