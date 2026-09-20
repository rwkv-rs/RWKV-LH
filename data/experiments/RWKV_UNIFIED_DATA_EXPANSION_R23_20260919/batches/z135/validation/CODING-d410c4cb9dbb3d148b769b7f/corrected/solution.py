import sys,math,functools
lines=iter(sys.stdin.buffer);sf,pf,gf=map(int,next(lines).split());total=sf+pf+gf;n=int(next(lines));bottles=[None];operations=[];directions=set()
for _ in range(n):
 v=next(lines).split()
 if v[0]==b'A':
  s,p,g=map(int,v[1:]);amount=s+p+g;x=s*total-sf*amount;y=p*total-pf*amount;div=math.gcd(x,y);direction=(x//div,y//div) if div else (0,0);bottles.append(direction);operations.append((1,direction))
  if div:directions.add(direction)
 else:operations.append((-1,bottles[int(v[1])]))
def half(v):return 0 if v[1]>0 or (v[1]==0 and v[0]>0) else 1
def compare(a,b):
 ha=half(a);hb=half(b)
 if ha!=hb:return -1 if ha<hb else 1
 cross=a[0]*b[1]-a[1]*b[0];return -1 if cross>0 else 1 if cross<0 else 0
directions=sorted(directions,key=functools.cmp_to_key(compare));index={v:i for i,v in enumerate(directions)};length=len(directions);counts=[0]*length;bit=[0]*(length+1);active=0;zeros=0;pairs=0;bad=0;out=[]
def add(i,delta):
 i+=1
 while i<=length:bit[i]+=delta;i+=i&-i

def prefix(i):
 value=0
 while i:value+=bit[i];i-=i&-i
 return value

def kth(k):
 pos=0;step=1<<(length.bit_length()-1)
 while step:
  nxt=pos+step
  if nxt<=length and bit[nxt]<=k:k-=bit[nxt];pos=nxt
  step//=2
 return pos

def gap(a,b):
 x,y=directions[a];xx,yy=directions[b];return int(x*yy-y*xx<=0)
for delta,direction in operations:
 if direction==(0,0):zeros+=delta
 else:
  i=index[direction];old=counts[i];new=old+delta;opposite=index.get((-direction[0],-direction[1]))
  if old==0:
   if opposite is not None and counts[opposite]:pairs+=1
   if not active:bad=1
   else:
    below=prefix(i);left=kth(below-1 if below else active-1);right=kth(below if below<active else 0);bad+=gap(left,i)+gap(i,right)-gap(left,right)
   add(i,1);active+=1
  elif new==0:
   if opposite is not None and counts[opposite]:pairs-=1
   if active==1:bad=0
   else:
    below=prefix(i);left=kth(below-1 if below else active-1);right=kth(below+1 if below+1<active else 0);bad+=gap(left,right)-gap(left,i)-gap(i,right)
   add(i,-1);active-=1
  counts[i]=new
 out.append('1' if zeros else '2' if pairs else '3' if active and bad==0 else '0')
print('\n'.join(out))
