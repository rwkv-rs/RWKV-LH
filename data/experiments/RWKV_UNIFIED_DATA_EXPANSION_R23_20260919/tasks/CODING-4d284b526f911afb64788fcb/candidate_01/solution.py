import sys
it=iter(map(int,sys.stdin.buffer.read().split()));answers=[]
for _ in range(next(it)):
 n=next(it);m=next(it);budget=next(it);grid=[[next(it) for _ in range(m)] for _ in range(n)];ones=((1<<(32*m))-1)//((1<<32)-1);guard=ones<<31;low=guard-ones
 def maximum(a,b):
  choose=((a|guard)-b)&guard;mask=choose-(choose>>31);return (a&mask)|(b&(low^mask))
 def pack(row):return int.from_bytes(b''.join(x.to_bytes(4,'little') for x in row),'little')
 packed=[pack(row) for row in grid];horizontal=[packed];vertical=[packed];half=1
 while half*2<=max(n,m):
  old=horizontal[-1];horizontal.append([maximum(row,row>>(32*half)) for row in old]);old=vertical[-1];vertical.append([maximum(old[i],old[i+half] if i+half<n else 0) for i in range(n)]);half*=2
 prefix=[0]
 for row in grid:
  sums=[0];value=0
  for x in row:value+=x;sums.append(value)
  prefix.append(prefix[-1]+pack(sums))
 need=packed[:];answer=0
 for radius in range((min(n,m)+1)//2):
  height=radius+1;width=2*radius+1;level=width.bit_length()-1;gap=width-(1<<level);shift=32*radius;validcols=m-2*radius;validguard=(((1<<(32*validcols))-1)//((1<<32)-1))<<31;threshold=height*(4*height*height-1)//3-budget;add=radius*ones;limit=(height*ones)|guard
  for center in range(radius,n-radius):
   top=center-radius;bottom=center+radius;a=horizontal[level][top];b=horizontal[level][bottom];edge=maximum(maximum(a,a>>(32*gap)),maximum(b,b>>(32*gap)))<<shift;v=maximum(vertical[level][top],vertical[level][top+gap]);edge=maximum(edge&low,maximum((v<<shift)&low,v>>shift));need[center]=maximum(need[center],edge+add);valid=((limit-need[center])&guard)>>shift
   if not valid&validguard:continue
   if threshold<=0:answer=height;continue
   strip=prefix[bottom+1]-prefix[top];sums=(strip>>(32*width))-strip;enough=((sums|validguard)-threshold*(validguard>>31))&validguard
   if valid&enough:answer=height
 answers.append(str(answer))
print('\n'.join(answers))
