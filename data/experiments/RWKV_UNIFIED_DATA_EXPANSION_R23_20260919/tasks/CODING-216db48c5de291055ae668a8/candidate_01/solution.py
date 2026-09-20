import sys

def distribution(roots,prime):
 # Difference tables advance many independent contiguous blocks in parallel.
 lanes=min(256,prime);steps=(prime+lanes-1)//lanes;degree=len(roots);coeff=[1]
 for root in roots:
  new=[0]*(len(coeff)+1)
  for i,c in enumerate(coeff):new[i]=(new[i]-root*c)%prime;new[i+1]=(new[i+1]+c)%prime
  coeff=new
 tables=[]
 for lane in range(lanes):
  values=[];start=lane*steps
  for x in range(start,start+degree+1):
   value=0
   for c in reversed(coeff):value=(value*x+c)%prime
   values.append(value)
  differences=[]
  while values:
   differences.append(values[0]);values=[(b-a)%prime for a,b in zip(values,values[1:])]
  tables.append(differences)
 width=max(1,((2*prime).bit_length()+1+7)//8);bits=8*width;guard=1<<(bits-1);ones=int.from_bytes(b''.join((1).to_bytes(width,'little') for _ in range(lanes)),'little');offset=(guard-prime)*ones;packed=[int.from_bytes(b''.join(tables[lane][i].to_bytes(width,'little') for lane in range(lanes)),'little') for i in range(degree+1)];frequency=[0]*prime
 for step in range(steps):
  data=packed[0].to_bytes(width*lanes,'little')
  for lane in range(lanes):
   if lane*steps+step<prime:frequency[int.from_bytes(data[lane*width:(lane+1)*width],'little')]+=1
  for i in range(degree):
   value=packed[i]+packed[i+1];over=((value+offset)>>(bits-1))&ones;packed[i]=value-prime*over
 return frequency
v=list(map(int,sys.stdin.buffer.read().split()));n,z=v[:2];prime=299993;points=list(zip(v[2::2],v[3::2]));a=2
while pow(a,(prime-1)//2,prime)!=prime-1:a+=1
imaginary=pow(a,(prime-1)//4,prime);left=[(x+imaginary*y)%prime for x,y in points];right=[(x-imaginary*y)%prime for x,y in points]
if z==0:
 l=len(set(left));r=len(set(right));print(prime*(l+r)-l*r);raise SystemExit
f=distribution(left,prime);g=distribution(right,prime);inverse=[0]*prime;inverse[1]=1
for i in range(2,prime):inverse[i]=prime-(prime//i)*inverse[prime%i]%prime
print(sum(f[i]*g[z*inverse[i]%prime] for i in range(1,prime)))
